from app import create_app

app = create_app()

if __name__ == '__main__':
    # Jalankan aplikasi menggunakan server development Flask,
    # karena flask-sock sudah terintegrasi dengan baik di sini.
    # Hindari menggunakan 'debug=True' di production.
    app.run(host='0.0.0.0', port=5000, debug=True)