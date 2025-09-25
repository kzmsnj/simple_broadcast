import os
from app import create_app, db
from flask_migrate import Migrate, upgrade

app = create_app()
# Pindahkan inisialisasi Migrate ke sini agar bisa diakses oleh terminal
migrate = Migrate(app, db)

# Terapkan migrasi saat aplikasi dimulai di server
# Hapus blok ini jika Anda ingin menjalankannya secara manual di server
with app.app_context():
    # Cek apakah folder migrasi ada sebelum upgrade
    if os.path.exists('migrations'):
        upgrade()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)