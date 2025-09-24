# app/subscriber/helpers.py

import pika
import json
from .. import RABBITMQ_HOST, NOTIF_EXCHANGE, online_users

def publish_to_rabbitmq(exchange, routing_key, body):
    """Fungsi umum untuk mempublikasikan pesan ke RabbitMQ."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='topic')
        channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body)
        connection.close()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error: Tidak dapat terhubung ke RabbitMQ. Detail: {e}")
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