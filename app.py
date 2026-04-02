import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from repository.database import db
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from lib.encryption import encrypt_message, decrypt_message

# Models

from models.chat import Chat
from models.message import Message
from models.chat_member import ChatMember
from models.message_deletion import MessageDeletion

# Routes

from routes.auth import auth_bp, login_manager
from routes.user import user_bp
from routes.chat import chat_bp

load_dotenv()

db_url = os.getenv("DATABASE_URL")
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

app = Flask(__name__)
CORS(app, origins=frontend_url, supports_credentials=True)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

socketio = SocketIO(app, cors_allowed_origins=frontend_url)

login_manager.init_app(app)
db.init_app(app)

@app.route('/health')
def health():
    return jsonify({"status": "OK"})

# Register blueprints

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(chat_bp)

# websocket

connected_users = {}  # sid -> user_id

def update_user_status(user_id, status):
    from models.user import User
    user = db.session.get(User, user_id)
    if user:
        user.status = status
        db.session.commit()
        emit('user_status_changed', {'user_id': user_id, 'status': status}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        from flask import request as flask_request
        connected_users[flask_request.sid] = current_user.id
        update_user_status(current_user.id, 'online')
        print(f'{current_user.username} online')

@socketio.on('user_away')
def handle_away():
    if current_user.is_authenticated:
        update_user_status(current_user.id, 'away')
        print(f'{current_user.username} away')

@socketio.on('user_online')
def handle_online():
    if current_user.is_authenticated:
        update_user_status(current_user.id, 'online')
        print(f'{current_user.username} back online')

@socketio.on('disconnect')
def handle_disconnect():
    from flask import request as flask_request
    user_id = connected_users.pop(flask_request.sid, None)
    if user_id:
        # Only set offline if user has no other connected tabs
        still_connected = any(uid == user_id for uid in connected_users.values())
        if not still_connected:
            update_user_status(user_id, 'offline')
            print(f'User {user_id} offline')


@socketio.on('join_chat')
def handle_join_chat(data):
    if current_user.is_authenticated:
        chat_id = data.get('chat_id')
        member = ChatMember.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
        if member:
            join_room(chat_id)
            print(f'{current_user.username} joined chat {chat_id}')

@socketio.on('leave_chat')
def handle_leave_chat(data):
    if current_user.is_authenticated:
        chat_id = data.get('chat_id')
        leave_room(chat_id)
        print(f'{current_user.username} left chat {chat_id}')

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        return

    chat_id = data.get('chat_id')
    content = data.get('content', '').strip()

    if not chat_id or not content:
        return

    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not member:
        return

    import uuid
    encrypted_content = encrypt_message(content)
    message = Message(
        id=str(uuid.uuid7()),
        chat_id=chat_id,
        sender_id=current_user.id,
        content=encrypted_content,
    )
    db.session.add(message)
    db.session.commit()

    emit('new_message', {
        'id': message.id,
        'chat_id': message.chat_id,
        'sender_id': message.sender_id,
        'content': content,
        'type': message.type,
        'reply_to_id': message.reply_to_id,
        'created_at': message.created_at.isoformat() if message.created_at else None,
    }, room=chat_id)

@socketio.on('edit_message')
def handle_edit_message(data):
    if not current_user.is_authenticated:
        return

    message_id = data.get('message_id')
    new_content = data.get('content', '').strip()

    if not message_id or not new_content:
        return

    message = db.session.get(Message,message_id)
    if not message or message.sender_id != current_user.id:
        return

    # Check if message was sent within 2 minutes
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    created = message.created_at.replace(tzinfo=timezone.utc) if message.created_at.tzinfo is None else message.created_at
    if (now - created).total_seconds() > 120:
        return

    message.content = encrypt_message(new_content)
    message.edited_at = now
    db.session.commit()

    emit('message_edited', {
        'id': message.id,
        'chat_id': message.chat_id,
        'content': new_content,
        'edited_at': message.edited_at.isoformat(),
    }, room=message.chat_id)

@socketio.on('delete_message')
def handle_delete_message(data):
    if not current_user.is_authenticated:
        return

    message_id = data.get('message_id')
    delete_for_all = data.get('delete_for_all', False)

    if not message_id:
        return

    message = db.session.get(Message,message_id)
    if not message:
        return

    from datetime import datetime, timezone
    import uuid

    if delete_for_all:
        # Only the sender can delete for all, and only within 5 minutes
        if message.sender_id != current_user.id:
            return

        now = datetime.now(timezone.utc)
        created = message.created_at.replace(tzinfo=timezone.utc) if message.created_at.tzinfo is None else message.created_at
        if (now - created).total_seconds() > 300:
            return

        message.deleted_at = now
        db.session.commit()

        emit('message_deleted', {
            'id': message_id,
            'chat_id': message.chat_id,
            'delete_for_all': True,
        }, room=message.chat_id)
    else:
        # Delete for me — per-user deletion record
        existing = MessageDeletion.query.filter_by(message_id=message_id, user_id=current_user.id).first()
        if not existing:
            deletion = MessageDeletion(
                id=str(uuid.uuid7()),
                message_id=message_id,
                user_id=current_user.id,
            )
            db.session.add(deletion)
            db.session.commit()

        emit('message_deleted', {
            'id': message_id,
            'chat_id': message.chat_id,
            'delete_for_all': False,
        })


if __name__ == '__main__':
    socketio.run(app, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")