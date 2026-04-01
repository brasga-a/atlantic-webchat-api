from repository.database import db

class Chat(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # e.g., "private", "group"
    name = db.Column(db.String(120), nullable=True)  # For group chats
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    members = db.relationship('ChatMember', backref='chat', lazy='dynamic')