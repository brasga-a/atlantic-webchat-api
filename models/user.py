from repository.database import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.String(40), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(120), nullable=False)