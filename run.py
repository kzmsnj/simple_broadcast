import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Honor PORT env var (e.g., for local container runs). Disable debug in prod.
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)