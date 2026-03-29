from repository.database import db

class ChatMember(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    chat_id = db.Column(db.String(40), db.ForeignKey('chat.id'), nullable=False)
    user_id = db.Column(db.String(40), db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # e.g., "admin", "member"
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_read_at = db.Column(db.DateTime, default=db.func.current_timestamp())