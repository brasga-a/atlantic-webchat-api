import base64
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, logout_user

from models import user
from models.user import User
from repository.database import db

user_bp = Blueprint('user', __name__, url_prefix='/user')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    user_data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "status": current_user.status
    }
    return jsonify(user_data), 200

@user_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PNG, JPG, GIF or WebP"}), 400

    mimetype = file.mimetype
    if mimetype not in ALLOWED_MIMETYPES:
        return jsonify({"error": "Invalid file type"}), 400

    file_data = file.read()
    b64 = base64.b64encode(file_data).decode('utf-8')
    avatar_url = f"data:{mimetype};base64,{b64}"

    user = db.session.get(User,current_user.id)
    user.avatar_url = avatar_url
    db.session.commit()

    return jsonify({"avatar_url": avatar_url}), 200

@user_bp.route('/update', methods=['PUT'])
@login_required
def update_profile():
    user = db.session.get(User,current_user.id)
    data = request.get_json()

    username = data.get('username')
    name = data.get('name')
    email = data.get('email')

    avatar = data.get('avatar_url')
    if avatar:
        user.avatar_url = avatar

    if username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({"error": "Username already exists"}), 400
        
        user.username = username
    
    if name:
        user.name = name

    if email: 
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({"error": "Email already exists"}), 400
        
        user.email = email

    db.session.commit()
    
    # Here you would typically save the user to the database
    # db.session.commit()

    return jsonify({"message": "Profile updated successfully"}), 200

@user_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"error": "Email parameter is required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    is_available = existing_user is None

    return jsonify({"available": is_available}), 200

@user_bp.route('/verify-username', methods=['POST'])
def verify_username():
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    existing_user = User.query.filter_by(username=username).first()
    is_available = existing_user is None

    return jsonify({"available": is_available}), 200

@user_bp.route('/<user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    user = db.session.get(User,user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "avatar_url": user.avatar_url,
    }), 200

@user_bp.route('/delete', methods=['DELETE'])
@login_required
def delete_profile():
    user = db.session.get(User,current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Profile deleted successfully"}), 200