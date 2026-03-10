"""API de subida y eliminación de imágenes en MinIO para el panel de administración.

Reglas de validación (servidor):
  - blog-cover  → WebP exactamente 1200 × 630 px
  - author-photo → WebP exactamente 400 × 400 px
"""
import io
from flask import jsonify, request
from flask_login import login_required
from PIL import Image

from app.services.minio_service import minio_service
from app.utils.logging_helper import log_activity
from .. import admin_bp

# ─── Especificaciones por tipo ─────────────────────────────────────────────────
_SPECS = {
    'blog-cover':    {'width': 1200, 'height': 630},
    'author-photo':  {'width': 400,  'height': 400},
}


def _validate_and_upload(file_storage, spec_key: str):
    """Lee el archivo, valida formato WebP y dimensiones, sube a MinIO.

    Returns (result_dict, error_str). Exactamente uno de ellos es None.
    """
    data = file_storage.read()

    # Validar con Pillow (ignora el MIME del navegador; usa magic bytes reales)
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return None, 'El archivo no es una imagen válida.'

    if img.format != 'WEBP':
        return None, (
            f'Solo se acepta formato WebP. '
            f'El archivo enviado es {img.format or "desconocido"}.'
        )

    spec = _SPECS[spec_key]
    if img.width != spec['width'] or img.height != spec['height']:
        return None, (
            f'Dimensiones incorrectas: se esperaba {spec["width"]} × {spec["height"]} px, '
            f'se recibió {img.width} × {img.height} px.'
        )

    # Subir a MinIO
    filename = minio_service.upload_file(data, 'image/webp')
    url = minio_service.get_file_url(filename)
    return {'url': url, 'key': filename}, None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@admin_bp.route('/api/upload/blog-cover', methods=['POST'])
@login_required
def upload_blog_cover():
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'ok': False, 'error': 'No se recibió ningún archivo.'}), 400

    result, error = _validate_and_upload(f, 'blog-cover')
    if error:
        return jsonify({'ok': False, 'error': error}), 422

    log_activity('UPLOAD_BLOG_COVER', f'Portada subida: {result["key"]}')
    return jsonify({'ok': True, **result})


@admin_bp.route('/api/upload/author-photo', methods=['POST'])
@login_required
def upload_author_photo():
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'ok': False, 'error': 'No se recibió ningún archivo.'}), 400

    result, error = _validate_and_upload(f, 'author-photo')
    if error:
        return jsonify({'ok': False, 'error': error}), 422

    log_activity('UPLOAD_AUTHOR_PHOTO', f'Foto de autora subida: {result["key"]}')
    return jsonify({'ok': True, **result})


@admin_bp.route('/api/upload', methods=['DELETE'])
@login_required
def delete_upload():
    data = request.get_json(silent=True) or {}
    key = (data.get('key') or '').strip()
    if not key:
        return jsonify({'ok': False, 'error': 'Falta el parámetro key.'}), 400

    ok = minio_service.remove_object(key)
    if ok:
        log_activity('UPLOAD_DELETE', f'Imagen eliminada de MinIO: {key}')
    return jsonify({'ok': ok})
