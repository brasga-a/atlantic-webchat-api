from repository.database import db

class Message(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    chat_id = db.Column(db.String(40), db.ForeignKey('chat.id'), nullable=False)
    sender_id = db.Column(db.String(40), db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='text')  # e.g., "text", "image", "file"
    reply_to_id = db.Column(db.String(40), db.ForeignKey('message.id'), nullable=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())