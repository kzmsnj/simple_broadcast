from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from ..models import Channel, Message, User
from .. import db, sock, RABBITMQ_HOST
from ..subscriber.helpers import publish_to_rabbitmq
import json
import pika
import threading
import time # Impor time

publisher_bp = Blueprint('publisher', __name__, url_prefix='/publisher')

# ... (semua kode dari @publisher_bp.route('/') hingga @publisher_bp.route('/stats') tetap sama) ...
# RUTE UTAMA: Menampilkan Dashboard Publisher
@publisher_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # --- TAMBAHKAN BLOK VALIDASI INI ---
    if not user:
        # Jika user dengan ID dari session tidak ada di DB,
        # bersihkan session dan paksa login ulang.
        session.clear()
        flash("Sesi Anda tidak valid, silakan login kembali.", "warning")
        return redirect(url_for('auth.login'))
    # --- AKHIR BLOK VALIDASI ---
    
    user_channels = Channel.query.filter_by(creator_id=user_id).order_by(Channel.created_at.desc()).all()
    total_messages_sent = db.session.query(Message).join(Channel).filter(Channel.creator_id == user_id).count()
    
    total_subscribers = sum(len(channel.subscribers) for channel in user.channels)
    
    stats = {
        'channel_count': len(user_channels),
        'messages_sent': total_messages_sent,
        'total_subscribers': total_subscribers
    }
    
    return render_template('publisher.html', channels=user_channels, stats=stats)

# RUTE UNTUK MENAMPILKAN FORM PEMBUATAN CHANNEL
@publisher_bp.route('/create', methods=['GET'])
def create_channel_form():
    """Hanya menampilkan halaman dengan form untuk membuat channel baru."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('create_channel.html')

# RUTE UNTUK MEMPROSES PEMBUATAN CHANNEL BARU
@publisher_bp.route('/create', methods=['POST'])
def create_channel_action():
    """Memproses data dari form pembuatan channel."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    channel_name = request.form.get('channel_name')
    description = request.form.get('description')
    
    if Channel.query.filter_by(name=channel_name).first():
        flash('Nama channel sudah ada, silakan pilih nama lain.', 'danger')
        return redirect(url_for('publisher.create_channel_form'))
    
    new_channel = Channel(
        name=channel_name,
        description=description,
        creator_id=session['user_id']
    )
    db.session.add(new_channel)
    db.session.commit()
    flash(f"Channel '{channel_name}' berhasil dibuat!", 'success')
    return redirect(url_for('publisher.dashboard'))
            
# RUTE UNTUK MENGIRIM PESAN (UNTUK AJAX/FETCH)
@publisher_bp.route('/send', methods=['POST'])
def send_message():
    """
    Menerima request pengiriman pesan dan mengembalikan data update
    dalam format JSON untuk pembaruan real-time di frontend.
    """
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    channel_id = request.form.get('channel_id')
    content = request.form.get('message_content')
    user_id = session['user_id']
    
    channel = Channel.query.get(channel_id)

    if not channel or channel.creator_id != user_id:
        return jsonify({'status': 'error', 'message': 'Invalid channel or permission denied'}), 403

    new_message = Message(
        channel_id=channel.id,
        username=session['username'],
        content=content
    )
    db.session.add(new_message)
    db.session.commit()

    chat_message = new_message.to_dict()
    routing_key = f"rooms.{channel.name}"
    publish_to_rabbitmq('webapp_exchange_rooms', routing_key, json.dumps(chat_message))
    
    total_messages_user = db.session.query(Message).join(Channel).filter(Channel.creator_id == user_id).count()
    total_messages_channel = Message.query.filter_by(channel_id=channel.id).count()
    
    return jsonify({
        'status': 'success',
        'message': f"Pesan terkirim ke '{channel.name}'!",
        'new_total_message_count': total_messages_user,
        'updated_channel_id': channel.id,
        'new_channel_message_count': total_messages_channel
    })

# ENDPOINT API UNTUK MENGAMBIL STATISTIK TERBARU
@publisher_bp.route('/stats')
def get_stats():
    """API endpoint untuk mengambil data statistik terbaru."""
    if 'user_id' not in session:
        return jsonify({}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({}), 404
    
    total_subscribers = sum(len(channel.subscribers) for channel in user.channels)
    
    return jsonify({
        'total_subscribers': total_subscribers
    })


# --- BLOK WEBSOCKET YANG DIPERBAIKI ---
@sock.route('/publisher/notifications')
def publisher_notifications(ws):
    """
    WebSocket endpoint untuk publisher mendengarkan update
    tentang subscription di channel-channel miliknya.
    """
    user_id = session.get('user_id')
    if not user_id:
        ws.close()
        return

    # Fungsi listener RabbitMQ tetap sama
    def rabbitmq_listener():
        try:
            params = pika.URLParameters(RABBITMQ_HOST)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange='webapp_exchange_notifications', exchange_type='topic')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            routing_key = f"user.{user_id}"
            channel.queue_bind(exchange='webapp_exchange_notifications', queue=queue_name, routing_key=routing_key)

            def callback(ch, method, properties, body):
                try:
                    # Cek koneksi sebelum mengirim
                    if ws.connected:
                        ws.send(body.decode('utf-8'))
                    else:
                        # Jika koneksi sudah ditutup, hentikan konsumsi pesan
                        ch.stop_consuming()
                except Exception:
                    ch.stop_consuming()
            
            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except Exception as e:
            print(f"Publisher listener error: {e}")

    listener_thread = threading.Thread(target=rabbitmq_listener)
    listener_thread.daemon = True
    listener_thread.start()

    # Loop utama yang sudah diperbaiki
    try:
        while ws.connected:
            # Tetap menerima pesan (jika ada) untuk menjaga koneksi tetap hidup
            # Timeout bisa disesuaikan, 1 detik sudah cukup
            ws.receive(timeout=1)
    except Exception:
        # Menangani jika koneksi terputus secara tidak normal
        pass
    finally:
        # Blok ini akan dijalankan saat loop berakhir (koneksi terputus)
        # Tidak perlu melakukan apa-apa di sini, thread akan berhenti sendiri
        pass