from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, logout_user

from models import user
from models.user import User
from repository.database import db

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    user_data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.name
    }
    return jsonify(user_data), 200

@user_bp.route('/update', methods=['PUT'])
@login_required
def update_profile():
    user = User.query.get(current_user.id)
    data = request.get_json()

    username = data.get('username')
    name = data.get('name')
    email = data.get('email')
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

@user_bp.route('/verify-username', methods=['POST'])
def verify_username():
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    existing_user = User.query.filter_by(username=username).first()
    is_available = existing_user is None

    return jsonify({"available": is_available}), 200

@user_bp.route('/delete', methods=['DELETE'])
@login_required
def delete_profile():
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Profile deleted successfully"}), 200