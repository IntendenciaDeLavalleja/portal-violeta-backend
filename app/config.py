import os
from dotenv import load_dotenv
from .redis_utils import build_redis_url_from_env

load_dotenv()

def _parse_list_from_env(name: str) -> list[str]:
    raw = os.environ.get(name)
    if raw:
        return [item.strip() for item in raw.split(',') if item.strip()]
    return []


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail Config
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # MinIO Config
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')
    MINIO_SECURE = os.environ.get('MINIO_SECURE', 'False') == 'True'
    MINIO_BUCKET_NAME = (
        os.environ.get('MINIO_BUCKET_NAME')
        or os.environ.get('MINIO_BUCKET')
        or 'ombudsman-uploads'
    )
    MINIO_PUBLIC_URL = (
        os.environ.get('MINIO_PUBLIC_URL')
        or os.environ.get('MINIO_PUBLIC_BASE_URL')
    )

    # Frontend URL for email links
    FRONTEND_URL = os.environ.get('FRONTEND_URL') or 'http://localhost:5173'

    # Redis Settings
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
    REDIS_DB = os.environ.get('REDIS_DB', '0')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    REDIS_URL = build_redis_url_from_env(os.environ)

    # Flask-Limiter
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    CORS_ALLOWED_ORIGINS = _parse_list_from_env('CORS_ORIGINS')
