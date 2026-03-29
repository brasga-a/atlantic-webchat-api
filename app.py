from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from repository.database import db
from routes.auth import auth_bp, login_manager
from routes.user import user_bp

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

db_url = os.getenv("DATABASE_URL")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

login_manager.init_app(app)
db.init_app(app)

@app.route('/health')
def health():
    return jsonify({"status": "OK"})

# Register blueprints

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)

if __name__ == '__main__':
    app.run(debug=True)