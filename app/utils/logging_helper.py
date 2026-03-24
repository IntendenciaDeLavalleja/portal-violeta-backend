from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.user import ActivityLog

def log_activity(action, details=None, user=None):
    """
    Registra una actividad en la base de datos con información forense.
    """
    try:
        # Si no se pasa un usuario explícitamente, intentar obtener el actual
        user_id = None
        username = "ANÓNIMO"
        
        if user:
            user_id = user.id
            username = user.username
        elif current_user and current_user.is_authenticated:
            user_id = current_user.id
            username = current_user.username
            
        # Obtener información de la petición
        ip = request.remote_addr
        user_agent = request.user_agent.string
        
        log = ActivityLog(
            user_id=user_id,
            username=username,
            action=action,
            details=details,
            ip_address=ip,
            user_agent=user_agent
        )
        
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Fallback para no romper el flujo principal si el logging falla
        print(f"Error registrando actividad: {e}")
