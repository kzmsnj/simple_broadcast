from . import db
from datetime import datetime

# Tabel perantara untuk relasi many-to-many antara User dan Channel
subscriptions = db.Table('subscriptions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('channel_id', db.Integer, db.ForeignKey('channel.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    # Relasi ke channel yang dibuat oleh user ini
    channels = db.relationship('Channel', backref='owner', lazy=True)
    # Relasi ke channel yang di-subscribe oleh user ini
    subscribed_channels = db.relationship('Channel', secondary=subscriptions, lazy='subquery',
        backref=db.backref('subscribers', lazy=True))

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='channel', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False) # Bisa diganti dengan user_id
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return { "type": "chat", "username": self.username, "message": self.content, "timestamp": self.timestamp.strftime("%H:%M") }