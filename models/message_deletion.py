from repository.database import db

class MessageDeletion(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    message_id = db.Column(db.String(40), db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.String(40), db.ForeignKey('user.id'), nullable=False)
    deleted_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    __table_args__ = (db.UniqueConstraint('message_id', 'user_id'),)
