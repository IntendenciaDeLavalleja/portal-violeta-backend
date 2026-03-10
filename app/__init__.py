from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db, migrate, login_manager, mail, ma, limiter, csrf
from .services.minio_service import minio_service
from .services.cache_service import cache_service
from .metrics import init_metrics
from .redis_utils import init_redis


def _init_limiter_safe(app):
    """
    Inicializa Flask-Limiter de forma segura.

    Intenta usar Redis como storage si está disponible.
    Si falla por cualquier motivo, fuerza el fallback a memory://
    y vuelve a inicializar. Nunca lanza excepciones.
    """
    redis_available = app.config.get('REDIS_AVAILABLE', False)
    redis_url = app.config.get('REDIS_URL', '')

    if redis_available and redis_url:
        app.config['RATELIMIT_STORAGE_URI'] = redis_url
    else:
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'

    try:
        limiter.init_app(app)
        storage_used = app.config['RATELIMIT_STORAGE_URI']
        app.logger.info(
            f"Flask-Limiter inicializado con storage: {storage_used}"
        )
    except Exception as exc:
        app.logger.warning(
            f"Flask-Limiter falló con storage actual: {exc}. "
            "Reintentando con memory://"
        )
        # Forzar fallback y reintentar una vez.
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
        try:
            limiter.init_app(app)
            app.logger.info(
                "Flask-Limiter inicializado con fallback memory://"
            )
        except Exception as exc2:
            # Último recurso: loguear y continuar sin Limiter funcional.
            app.logger.error(
                f"Flask-Limiter no pudo inicializarse: {exc2}. "
                "Rate limiting deshabilitado para esta sesión."
            )


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../public', static_url_path='/public')
    app.config.from_object(config_class)

    # Probar Redis y almacenar disponibilidad en app.config['REDIS_AVAILABLE'].
    # init_redis() nunca lanza excepciones: es seguro siempre.
    init_redis(app)

    # Habilitar CORS
    CORS(
        app,
        resources={
            r"/api/*": {"origins": app.config.get('CORS_ALLOWED_ORIGINS', [])}
        },
        supports_credentials=True
    )

    # Inicializar extensiones base
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    ma.init_app(app)
    csrf.init_app(app)

    # Inicializar Flask-Limiter con fallback automático a memory://.
    _init_limiter_safe(app)

    # Inicializar servicios (todos con fallback interno)
    try:
        minio_service.init_app(app)
    except Exception as exc:
        app.logger.warning(
            "MinIO no disponible al iniciar, "
            f"se continúa sin cliente: {exc}"
        )

    cache_service.init_app(app)

    # Inicializar monitoreo
    init_metrics(app)

    # Registrar blueprints
    from .health import health_bp
    csrf.exempt(health_bp)
    app.register_blueprint(health_bp)

    from .api import api_bp
    csrf.exempt(api_bp)  # Eximir API de protección CSRF (usa tokens Bearer)
    app.register_blueprint(api_bp, url_prefix='/api')

    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Registrar comandos CLI
    from .commands import (
        create_admin,
        init_db,
        archive_expired_pre_reservations_command,
    )
    app.cli.add_command(create_admin)
    app.cli.add_command(init_db)
    app.cli.add_command(archive_expired_pre_reservations_command)

    # Cargar modelos para migraciones
    import importlib
    importlib.import_module('app.models')

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import AdminUser

    return AdminUser.query.get(int(user_id))
