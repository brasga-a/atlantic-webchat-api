
from flask import Blueprint, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bcrypt import checkpw, hashpw, gensalt
from models.user import User
from repository.database import db
import uuid


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

login_manager = LoginManager()

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "Authentication required"}), 401

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')  # Can be either username or email
    password = data.get('password')

    if identifier and password: 
        user = User.query.filter_by(username=identifier).first() or User.query.filter_by(email=identifier).first()
        check_password = checkpw(str.encode(password), str.encode(user.password)) if user else False

        if user and check_password:
            login_user(user)
            return jsonify({"message": "Login successful"}), 200

        return jsonify({"message": "Invalid username or password"}), 401

    return jsonify({"message": "Invalid credentials"}), 401 

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not username or not email or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400

    if password != confirm_password: 
            return jsonify({"message": "Passwords do not match"}), 400

    if username and email and password and confirm_password:
    
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
    
        if existing_user:
            return jsonify({"message": "Username already exists"}), 400

        if existing_email:
            return jsonify({"message": "Email already exists"}), 400

        hashed_password = hashpw(str.encode(password), gensalt()).decode('utf-8')

        new_user = User(id=str(uuid.uuid7()), username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        user = User.query.filter_by(username=new_user.username).first()
        login_user(user)
        return jsonify({"message": "User registered successfully"}), 201

    return jsonify({"message": "Invalid credentials"}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200
