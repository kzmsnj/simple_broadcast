from app import create_app

app = create_app()

if __name__ == '__main__':
    # 'app' di sini adalah instance Flask dari create_app()
    # Untuk menjalankan dengan WebSocket, kita perlu sedikit modifikasi
    # atau menggunakan production server seperti Gunicorn dengan eventlet/gevent
    app.run(host='0.0.0.0', port=5000, debug=True)