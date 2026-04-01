from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from models.user import User
from repository.database import db
from models.chat import Chat
from models.chat_member import ChatMember
from models.message import Message
from lib.encryption import decrypt_message
from models.message_deletion import MessageDeletion
import uuid

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/create', methods=['POST'])
@login_required
def create_chat():
    data = request.get_json()
    identifier = data.get("identifier")

    if not identifier:
        return jsonify({"error": "Username or email is required."}), 400

    # Find user by username or email
    other_user = User.query.filter_by(username=identifier).first()
    if not other_user:
        other_user = User.query.filter_by(email=identifier).first()

    if not other_user:
        return jsonify({"error": "User not found."}), 404

    if other_user.id == current_user.id:
        return jsonify({"error": "You cannot create a chat with yourself."}), 400

    # Check if a private chat already exists between these two users
    existing_chat = Chat.query.join(ChatMember).filter(
        ChatMember.user_id == current_user.id,
        Chat.type == "private"
    ).all()

    for c in existing_chat:
        other_member = ChatMember.query.filter(
            ChatMember.chat_id == c.id,
            ChatMember.user_id == other_user.id
        ).first()
        if other_member:
            return jsonify({"message": "Chat already exists.", "chat_id": c.id}), 200

    new_chat = Chat(id=str(uuid.uuid7()), type="private")
    db.session.add(new_chat)

    member1 = ChatMember(id=str(uuid.uuid7()), chat_id=new_chat.id, user_id=current_user.id)
    member2 = ChatMember(id=str(uuid.uuid7()), chat_id=new_chat.id, user_id=other_user.id)

    db.session.add(member1)
    db.session.add(member2)
    db.session.commit()

    return jsonify({"message": "Chat created successfully.", "chat_id": new_chat.id}), 201

@chat_bp.route('/list', methods=['GET'])
@login_required
def get_chats():
    user_chats = Chat.query.join(ChatMember).filter(ChatMember.user_id == current_user.id).all()
    chat_list = []
    for chat in user_chats:
        # Get last message excluding ones deleted by the current user
        deleted_for_me = db.session.query(MessageDeletion.message_id).filter_by(user_id=current_user.id).subquery()
        last_message = Message.query.filter_by(chat_id=chat.id).filter(
            ~Message.id.in_(db.session.query(deleted_for_me))
        ).order_by(Message.created_at.desc()).first()

        # For private chats, show the other person's name and avatar
        chat_name = chat.name
        chat_username = None
        chat_avatar = None
        contact_id = None
        chat_status = None
        if chat.type == "private":
            other_member = ChatMember.query.filter(
                ChatMember.chat_id == chat.id,
                ChatMember.user_id != current_user.id
            ).first()
            if other_member:
                other_user = db.session.get(User,other_member.user_id)
                contact_id = other_user.id
                chat_name = other_user.name or other_user.username
                chat_username = other_user.username
                chat_avatar = other_user.avatar_url
                chat_status = other_user.status

        chat_list.append({
            "id": chat.id,
            "type": chat.type,
            "name": chat_name,
            "status": chat_status,
            "username": chat_username,
            "contact_id": contact_id,
            "avatar_url": chat_avatar,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "chat_img": f"/chat/{chat.id}",
            "last_message": {
                "content": "Deleted message" if last_message.deleted_at else decrypt_message(last_message.content),
                "sender_id": last_message.sender_id,
                "created_at": last_message.created_at
            } if last_message else None
        })
    return jsonify(chat_list), 200

@chat_bp.route('/<chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    # Verify user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not member:
        return jsonify({"error": "You are not a member of this chat."}), 403

    limit = request.args.get('limit', 50, type=int)
    before = request.args.get('before', None)

    # Get message IDs the current user has deleted for themselves
    deleted_for_me = db.session.query(MessageDeletion.message_id).filter_by(user_id=current_user.id).subquery()

    query = Message.query.filter_by(chat_id=chat_id).filter(
        ~Message.id.in_(db.session.query(deleted_for_me))
    )

    if before:
        ref_message = db.session.get(Message, before)
        if ref_message:
            query = query.filter(Message.created_at < ref_message.created_at)

    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    messages.reverse()

    return jsonify([{
        "id": m.id,
        "chat_id": m.chat_id,
        "sender_id": m.sender_id,
        "content": "Deleted message" if m.deleted_at else decrypt_message(m.content),
        "type": m.type,
        "reply_to_id": m.reply_to_id,
        "edited_at": m.edited_at.isoformat() if m.edited_at else None,
        "deleted_at": m.deleted_at.isoformat() if m.deleted_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in messages]), 200