from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from ..models import Channel, Message
from .. import db
# Kita butuh helper RabbitMQ untuk mengirim pesan
from ..subscriber.helpers import publish_to_rabbitmq
import json

publisher_bp = Blueprint('publisher', __name__, url_prefix='/publisher')

# RUTE UTAMA: Menampilkan Dashboard Publisher
@publisher_bp.route('/')
def dashboard():
    """
    Menampilkan halaman utama "Studio Broadcast".
    Mengambil data channel dan statistik pesan yang dimiliki oleh pengguna.
    """
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    username = session['username']
    # Ambil semua channel yang dibuat oleh pengguna yang sedang login
    user_channels = Channel.query.filter_by(creator=username).order_by(Channel.created_at.desc()).all()
    
    # Hitung total pesan yang dikirim oleh pengguna ini dari semua channel miliknya
    total_messages_sent = db.session.query(Message).join(Channel).filter(Channel.creator == username).count()
    
    stats = {
        'channel_count': len(user_channels),
        'messages_sent': total_messages_sent
    }
    
    return render_template('publisher.html', channels=user_channels, stats=stats)

# RUTE UNTUK MENAMPILKAN FORM PEMBUATAN CHANNEL
@publisher_bp.route('/create', methods=['GET'])
def create_channel_form():
    """Hanya menampilkan halaman dengan form untuk membuat channel baru."""
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    return render_template('create_channel.html')

# RUTE UNTUK MEMPROSES PEMBUATAN CHANNEL BARU
@publisher_bp.route('/create', methods=['POST'])
def create_channel_action():
    """Memproses data dari form pembuatan channel."""
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    channel_name = request.form.get('channel_name')
    description = request.form.get('description')
    
    if Channel.query.filter_by(name=channel_name).first():
        flash('Nama channel sudah ada, silakan pilih nama lain.', 'danger')
        return redirect(url_for('publisher.create_channel_form'))
    
    new_channel = Channel(
        name=channel_name,
        description=description,
        creator=session['username']
    )
    db.session.add(new_channel)
    db.session.commit()
    flash(f"Channel '{channel_name}' berhasil dibuat!", 'success')
    # Kembali ke dashboard setelah berhasil membuat channel
    return redirect(url_for('publisher.dashboard'))
            
# RUTE UNTUK MENGIRIM PESAN (UNTUK AJAX/FETCH)
@publisher_bp.route('/send', methods=['POST'])
def send_message():
    """
    Menerima request pengiriman pesan, menyimpannya, menyiarkannya,
    dan mengembalikan data update yang lebih detail dalam format JSON.
    """
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    channel_id = request.form.get('channel_id')
    content = request.form.get('message_content')
    username = session['username']
    
    channel = Channel.query.get(channel_id)

    if not channel or channel.creator != username:
        return jsonify({'status': 'error', 'message': 'Invalid channel or permission denied'}), 403

    # 1. Simpan pesan ke database
    new_message = Message(
        channel_id=channel.id,
        username=username,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()

    # 2. Siarkan pesan ke RabbitMQ
    chat_message = new_message.to_dict()
    routing_key = f"rooms.{channel.name}"
    publish_to_rabbitmq('webapp_exchange_rooms', routing_key, json.dumps(chat_message))
    
    # 3. Hitung kembali total pesan dan kirim sebagai respons JSON
    total_messages_user = db.session.query(Message).join(Channel).filter(Channel.creator == username).count()
    
    # --- TAMBAHAN BARU: Hitung pesan untuk channel spesifik ini ---
    total_messages_channel = Message.query.filter_by(channel_id=channel.id).count()
    
    return jsonify({
        'status': 'success',
        'message': f"Pesan terkirim ke '{channel.name}'!",
        'new_total_message_count': total_messages_user,
        # --- TAMBAHAN BARU: Kirim data update untuk channel ---
        'updated_channel_id': channel.id,
        'new_channel_message_count': total_messages_channel
    })