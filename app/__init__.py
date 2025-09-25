import os
from flask import Flask
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
sock = Sock()

online_users = {}
RABBITMQ_HOST = os.environ.get('CLOUDAMQP_URL', 'amqps://boxyswfe:c_0Y3HYRm3BcSeMINvdarthrlQOapZ8q@armadillo.rmq.cloudamqp.com/boxyswfe')
CHAT_EXCHANGE = 'webapp_exchange_rooms'
NOTIF_EXCHANGE = 'webapp_exchange_notifications'

def create_app():
    app = Flask(__name__)
    # Ini akan menunjuk ke folder root proyek Anda (D:\pro_messaging_app)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-aman'
    
    # --- BLOK YANG DIPERBAIKI ---
    # Prioritaskan DATABASE_URL untuk lingkungan produksi.
    # Jika tidak ada, gunakan file chat.db di folder proyek untuk development lokal.
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Gunakan URL dari environment variable jika ada (untuk produksi)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Gunakan path lokal jika tidak ada (untuk development)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'chat.db')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    sock.init_app(app)
    Migrate(app, db)

    with app.app_context():
        from .auth.routes import auth_bp
        app.register_blueprint(auth_bp)

        from .publisher.routes import publisher_bp
        app.register_blueprint(publisher_bp)
        
        from .subscriber.routes import subscriber_bp
        app.register_blueprint(subscriber_bp)

        db.create_all()

        return app
