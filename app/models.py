from . import db
from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # --- TAMBAHKAN METHOD INI ---
    def to_dict(self):
        """Mengubah objek Message menjadi dictionary."""
        return {
            "type": "chat",
            "username": self.username,
            "message": self.content,
            "timestamp": self.timestamp.strftime("%H:%M")
        }

class Channel(db.Model):
    # ... (sisa kode di sini tetap sama) ...
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    creator = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='channel', lazy=True)