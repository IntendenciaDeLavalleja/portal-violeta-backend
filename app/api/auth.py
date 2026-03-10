from flask import jsonify, request, session
from app.models.user import AdminUser, TwoFactorCode
from app.services.email_service import send_2fa_email
from app.extensions import db, limiter
from app.utils.logging_helper import log_activity
import secrets
from datetime import datetime
from . import api_bp

@api_bp.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_login():
    """Login exclusivo para la aplicación Electron (JSON)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se proporcionaron datos JSON"}), 400
        
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Correo electrónico y contraseña requeridos"}), 400

    user = AdminUser.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        # Step 1: Valid credentials, start 2FA
        # Note: For API, we can either use session or a temporary token.
        # For now, keeping session for consistency, but Electron can handle it.
        session['api_2fa_user_id'] = user.id
        
        # Generate 6-digit code
        code = ''.join([secrets.choice('0123456789') for _ in range(6)])
        
        # Save code in DB
        tf_code = TwoFactorCode(user_id=user.id, code=code)
        db.session.add(tf_code)
        db.session.commit()
        
        # Send mail
        send_2fa_email(user.email, code)
        
        log_activity("API_LOGIN_STEP1_SUCCESS", f"Credenciales API válidas. 2FA enviado a {user.email}", user)
        return jsonify({
            "success": True, 
            "message": "Código 2FA enviado",
            "email_preview": f"{user.email[:3]}...{user.email[-4:]}"
        }), 200
        
    log_activity("API_LOGIN_FAIL", f"Intento de login API fallido: {email}")
    return jsonify({"success": False, "error": "Correo electrónico o contraseña inválidos"}), 401

@api_bp.route('/auth/verify-2fa', methods=['POST'])
@limiter.limit("10 per minute")
def api_verify_2fa():
    """Verificación de 2FA para la aplicación Electron."""
    if 'api_2fa_user_id' not in session:
        return jsonify({"error": "Sesión expirada o inválida"}), 401
        
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "Código de verificación requerido"}), 400
        
    user_id = session.get('api_2fa_user_id')
    user = AdminUser.query.get(user_id)
    
    if not user:
        session.pop('api_2fa_user_id', None)
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    # Find the latest unconsumed code
    tf_code = TwoFactorCode.query.filter_by(user_id=user.id, consumed_at=None)\
        .order_by(TwoFactorCode.created_at.desc()).first()
        
    if tf_code and tf_code.verify_code(code):
        tf_code.consumed_at = datetime.utcnow()
        db.session.commit()
        
        # Here we could return a JWT token for the Electron app
        # For now, we use Flask-Login session if the Electron app handles cookies
        from flask_login import login_user
        login_user(user)
        session.pop('api_2fa_user_id', None)
        
        log_activity("API_LOGIN_2FA_SUCCESS", "API 2FA Exitosa.", user)
        
        return jsonify({
            "success": True,
            "message": "Sesión iniciada correctamente",
            "user": {
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser
            }
        }), 200
    else:
        log_activity("API_LOGIN_2FA_FAIL", f"Código API 2FA incorrecto para usuario ID: {user_id}", user)
        return jsonify({"success": False, "error": "Código inválido o expirado"}), 400
