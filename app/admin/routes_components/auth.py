from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models.user import AdminUser, TwoFactorCode
from app.services.email_service import send_2fa_email
from app.utils.logging_helper import log_activity
from .. import admin_bp
from datetime import datetime
import secrets
import random

@admin_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('admin.dashboard'))
        
        # Generar captcha aritmético simple
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        session['captcha_result'] = num1 + num2
        captcha_question = f"¿Cuánto es {num1} + {num2}?"
        
        return render_template('admin/login.html', captcha_question=captcha_question)

    # Manejar POST
    email = (request.form.get('email') or '').strip()
    password = (request.form.get('password') or '').strip()
    captcha_answer = (request.form.get('captcha') or '').strip()

    if not email or not password or not captcha_answer:
        flash('Completá email, contraseña y captcha.', 'error')

        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        session['captcha_result'] = num1 + num2
        captcha_question = f"¿Cuánto es {num1} + {num2}?"
        return render_template('admin/login.html', captcha_question=captcha_question)
    
    # Verificar Captcha
    stored_captcha = session.get('captcha_result')
    if captcha_answer is None or str(captcha_answer) != str(stored_captcha):
        session.pop('captcha_result', None)
        log_activity("ADMIN_LOGIN_CAPTCHA_FAIL", f"Captcha fallido para: {email}")
        flash('Captcha incorrecto. Intenta de nuevo.', 'error')
        
        # Generar nuevo captcha para el reintento
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        session['captcha_result'] = num1 + num2
        captcha_question = f"¿Cuánto es {num1} + {num2}?"
        
        return render_template('admin/login.html', captcha_question=captcha_question)

    session.pop('captcha_result', None)

    user = AdminUser.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['2fa_user_id'] = user.id
        code = ''.join([secrets.choice('0123456789') for _ in range(6)])
        tf_code = TwoFactorCode(user_id=user.id, code=code)
        db.session.add(tf_code)
        db.session.commit()
        send_2fa_email(user.email, code)
        log_activity("ADMIN_LOGIN_STEP1_SUCCESS", f"Código 2FA enviado a {user.email}", user)
        return redirect(url_for('admin.verify_2fa'))
    
    log_activity("ADMIN_LOGIN_FAIL", f"Intento fallido: {email}")
    flash('Usuario o contraseña incorrectos', 'error')
    
    # Generar nuevo captcha para el reintento
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_result'] = num1 + num2
    captcha_question = f"¿Cuánto es {num1} + {num2}?"
    
    return render_template('admin/login.html', captcha_question=captcha_question)

@admin_bp.route('/verify-2fa', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verify_2fa():
    if '2fa_user_id' not in session:
        return redirect(url_for('admin.login'))
        
    if request.method == 'POST':
        code = (request.form.get('code') or '').strip()
        user_id = session.get('2fa_user_id')
        user = AdminUser.query.get(user_id)

        if not code:
            flash('Ingresá el código de verificación.', 'error')
            return render_template('admin/2fa.html')

        if not code.isdigit() or len(code) != 6:
            flash('El código debe tener 6 dígitos numéricos.', 'error')
            return render_template('admin/2fa.html')
        
        if not user:
            session.pop('2fa_user_id', None)
            return redirect(url_for('admin.login'))
            
        tf_code = TwoFactorCode.query.filter_by(user_id=user.id, consumed_at=None)\
            .order_by(TwoFactorCode.created_at.desc()).first()
            
        if tf_code and tf_code.verify_code(code):
            tf_code.consumed_at = datetime.utcnow()
            db.session.commit()
            login_user(user)
            session.pop('2fa_user_id', None)
            log_activity("ADMIN_LOGIN_2FA_SUCCESS", "Sesión iniciada.", user)
            return redirect(url_for('admin.dashboard'))
        else:
            log_activity("ADMIN_LOGIN_2FA_FAIL", f"2FA incorrecto para usuario ID: {user_id}", user)
            flash('Código inválido o expirado', 'error')
            
    return render_template('admin/2fa.html')

@admin_bp.route('/logout')
@login_required
def logout():
    log_activity("ADMIN_LOGOUT", "Cierre de sesión.")
    logout_user()
    return redirect(url_for('admin.login'))
