from minio import Minio
from minio.error import S3Error
from flask import current_app
import io
import uuid
from urllib.parse import urlparse

class MinioService:
    def __init__(self, app=None):
        self.client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        minio_endpoint = app.config.get('MINIO_ENDPOINT')
        access_key = app.config.get('MINIO_ACCESS_KEY')
        secret_key = app.config.get('MINIO_SECRET_KEY')
        secure = app.config.get('MINIO_SECURE', False)
        
        if minio_endpoint and access_key and secret_key:
            self.client = Minio(
                minio_endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            self._ensure_bucket_exists(app.config.get('MINIO_BUCKET_NAME'))

    def _ensure_bucket_exists(self, bucket_name):
        if not self.client:
            return
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
            
            # Asegurar SIEMPRE política pública para lectura (evita que las imágenes "vencen"
            # si alguien cambia la política manualmente a privada)
            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}"]
                    },
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(bucket_name, json.dumps(policy))
        except S3Error as e:
            print(f"Error checking/creating bucket: {e}")

    def upload_file(self, file_data, content_type, bucket_name=None):
        if not self.client:
            raise Exception("MinIO client not initialized")

        if content_type != 'image/webp':
            raise ValueError('Solo se permiten imágenes en formato WEBP')
        
        bucket = bucket_name or current_app.config['MINIO_BUCKET_NAME']
        
        # Generar nombre único
        filename = f"{uuid.uuid4()}"
        ext = content_type.split('/')[-1] if '/' in content_type else ''
        if ext:
            filename += f".{ext}"

        # Preparar stream
        if isinstance(file_data, bytes):
            file_stream = io.BytesIO(file_data)
            length = len(file_data)
        else:
            # Asumimos que es un objeto FileStorage de Flask
            file_stream = file_data.stream
            # Mover cursor al final para obtener longitud
            file_data.seek(0, 2) 
            length = file_data.tell()
            file_data.seek(0)

        self.client.put_object(
            bucket,
            filename,
            file_stream,
            length,
            content_type=content_type
        )
        
        return filename

    def list_objects(self, bucket_name=None):
        if not self.client:
            return []

        bucket = bucket_name or current_app.config['MINIO_BUCKET_NAME']
        return list(self.client.list_objects(bucket, recursive=True))

    def remove_object(self, object_name, bucket_name=None):
        if not self.client:
            return False

        bucket = bucket_name or current_app.config['MINIO_BUCKET_NAME']
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except Exception:
            return False

    def get_file_url(self, filename, bucket_name=None):
        """
        Construye la URL pública de un objeto en MinIO.

        Formato: {MINIO_PUBLIC_URL}/{MINIO_BUCKET_NAME}/{filename}

        MINIO_PUBLIC_URL es la URL expuesta por Traefik/proxy (con https://).
        MINIO_ENDPOINT es solo para la conexión interna de subida, nunca
        se usa para generar URLs públicas.
        """
        bucket = bucket_name or current_app.config['MINIO_BUCKET_NAME']
        public_base = current_app.config.get(
            'MINIO_PUBLIC_URL', ''
        ).rstrip('/')

        if public_base:
            parsed = urlparse(public_base)
            path_parts = [part for part in parsed.path.split('/') if part]

            # Si el public_base ya incluye el bucket, no duplicarlo.
            if path_parts and path_parts[-1] == bucket:
                return f"{public_base}/{filename}"

            return f"{public_base}/{bucket}/{filename}"

        # Fallback cuando no hay MINIO_PUBLIC_URL configurada (desarrollo local).
        # Construye la URL usando el endpoint interno con el protocolo correcto.
        endpoint = current_app.config['MINIO_ENDPOINT']
        protocol = "https" if current_app.config.get('MINIO_SECURE', False) else "http"
        return f"{protocol}://{endpoint}/{bucket}/{filename}"

minio_service = MinioService()
