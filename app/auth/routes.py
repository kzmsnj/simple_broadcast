from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..models import User # Impor model User
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            # Cari user di database
            user = User.query.filter_by(username=username).first()
            # Jika tidak ada, buat user baru
            if not user:
                user = User(username=username)
                db.session.add(user)
                db.session.commit()
            
            # Simpan user ID di session
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f"Halo, {username}! Selamat datang kembali.", "success")
            return redirect(url_for('auth.dashboard'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', username=session['username'])