import pika
import json
from .. import RABBITMQ_HOST, NOTIF_EXCHANGE, online_users

def publish_to_rabbitmq(exchange, routing_key, body):
    """
    Fungsi umum untuk mempublikasikan pesan ke RabbitMQ.
    Sudah disesuaikan untuk menggunakan URL koneksi lengkap dari environment variable.
    """
    try:
        # PERUBAHAN UTAMA: Gunakan pika.URLParameters untuk membaca URL lengkap
        # Variabel RABBITMQ_HOST sekarang bisa berisi URL dari CloudAMQP atau 'localhost'
        params = pika.URLParameters(RABBITMQ_HOST)
        
        # Buat koneksi menggunakan parameter tersebut
        connection = pika.BlockingConnection(params)
        
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='topic')
        channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body)
        connection.close()
    except Exception as e:
        print(f"Terjadi error saat publish ke RabbitMQ: {e}")


def broadcast_user_list(room_name):
    """Mengambil daftar pengguna dari state dan menyiarkannya."""
    users = list(online_users.get(room_name, set()))
    
    message = {
        "type": "update-users",
        "users": users
    }
    
    routing_key = f"rooms.{room_name}"
    
    publish_to_rabbitmq(NOTIF_EXCHANGE, routing_key, json.dumps(message))