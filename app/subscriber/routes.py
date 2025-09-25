from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, current_app
from ..models import Channel, Message, User
from .. import db, sock, online_users, RABBITMQ_HOST
from .helpers import publish_to_rabbitmq, broadcast_user_list
import json
import pika
import threading

subscriber_bp = Blueprint('subscriber', __name__, url_prefix='/subscriber')

# Rute utama untuk menampilkan dashboard subscriber
@subscriber_bp.route('/')
def dashboard():
    """
    Menampilkan halaman dashboard utama untuk subscriber.
    Memerlukan pengguna untuk login (berdasarkan 'user_id' di session).
    Mengambil semua channel dan data subscription pengguna.
    """
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Ambil objek user yang sedang login dari database
    user = User.query.get(session['user_id'])
    if not user:
        # Jika user tidak ditemukan (misal: session lama), paksa login ulang
        session.clear()
        return redirect(url_for('auth.login'))

    all_channels = Channel.query.order_by(Channel.created_at.desc()).all()
    
    # Ambil semua ID channel yang sudah di-subscribe oleh user ini
    subscribed_channel_ids = {channel.id for channel in user.subscribed_channels}
    
    return render_template('subscriber.html', channels=all_channels, subscribed_channel_ids=subscribed_channel_ids)

# API Endpoint untuk menangani aksi Subscribe dan Unsubscribe
@subscriber_bp.route('/toggle_subscription', methods=['POST'])
def toggle_subscription():
    """
    Menangani penambahan atau penghapusan subscription.
    Dipanggil oleh JavaScript (Fetch API) saat tombol diklik.
    """
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json()
    channel_id = data.get('channel_id')
    
    user = User.query.get(session['user_id'])
    channel = Channel.query.get(channel_id)

    if not channel:
        return jsonify({'status': 'error', 'message': 'Channel not found'}), 404

    # Cek apakah user sudah subscribe ke channel ini
    if channel in user.subscribed_channels:
        # Jika sudah, lakukan unsubscribe
        user.subscribed_channels.remove(channel)
        action = 'unsubscribed'
    else:
        # Jika belum, lakukan subscribe
        user.subscribed_channels.append(channel)
        action = 'subscribed'
    
    db.session.commit()

    # --- PENYESUAIAN TERBARU: Kirim notifikasi ke RabbitMQ ---
    owner_id = channel.creator_id
    notification_message = {
        "type": "subscription_update",
        "owner_id": owner_id
    }
    publish_to_rabbitmq(
        exchange='webapp_exchange_notifications', 
        routing_key=f"user.{owner_id}", 
        body=json.dumps(notification_message)
    )
    
    # Kembalikan respons JSON ke frontend
    return jsonify({
        'status': 'success',
        'action': action,
        'subscription_count': len(user.subscribed_channels)
    })

# Rute untuk menangani koneksi WebSocket real-time
@sock.route('/subscribe')
def subscribe(ws):
    """
    Menangani koneksi WebSocket. Dijalankan oleh JavaScript
    setelah pengguna berhasil subscribe ke sebuah channel.
    """
    room_name = request.args.get('room')
    username = request.args.get('username')
    if not room_name or not username:
        ws.close(); return

    # Logika Pengguna Online (Bergabung)
    if room_name not in online_users:
        online_users[room_name] = set()
    online_users[room_name].add(username)
    broadcast_user_list(room_name)
    
    # Mengirim Riwayat Pesan
    with current_app.app_context():
        history = Message.query.join(Channel).filter(Channel.name == room_name).order_by(Message.timestamp.asc()).limit(50).all()
        for msg in history:
            hist_msg = msg.to_dict()
            hist_msg['type'] = 'history'
            try:
                ws.send(json.dumps(hist_msg))
            except Exception:
                break

    # Listener RabbitMQ di thread terpisah
    def rabbitmq_listener():
        try:
            params = pika.URLParameters(RABBITMQ_HOST)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange='webapp_exchange_rooms', exchange_type='topic')
            channel.exchange_declare(exchange='webapp_exchange_notifications', exchange_type='topic')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            routing_key = f"rooms.{room_name}"
            channel.queue_bind(exchange='webapp_exchange_rooms', queue=queue_name, routing_key=routing_key)
            channel.queue_bind(exchange='webapp_exchange_notifications', queue=queue_name, routing_key=routing_key)
            
            def callback(ch, method, properties, body):
                try: 
                    ws.send(body.decode('utf-8'))
                except Exception:
                    ch.stop_consuming()
            
            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except Exception as e:
            print(f"RabbitMQ listener error: {e}")

    listener_thread = threading.Thread(target=rabbitmq_listener)
    listener_thread.daemon = True
    listener_thread.start()

    try:
        while True:
            ws.receive(timeout=None)
    except Exception:
        pass
    finally:
        # Logika Pengguna Online (Keluar)
        if room_name in online_users and username in online_users[room_name]:
            online_users[room_name].remove(username)
            if not online_users[room_name]:
                del online_users[room_name]
            broadcast_user_list(room_name)