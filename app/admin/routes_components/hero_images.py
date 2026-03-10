from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.services.cache_service import cache_service
from app.models.camping import HeroImage, MediaAsset
from app.utils.logging_helper import log_activity
from app.services.minio_service import minio_service
from .. import admin_bp

@admin_bp.route('/camping/hero-images', methods=['GET', 'POST'])
@login_required
def camping_hero_images():
    if request.method == 'POST':
        uploaded = request.files.get('hero_image')
        if not uploaded or not uploaded.filename:
            flash('Selecciona una imagen para subir', 'error')
            return redirect(url_for('admin.camping_hero_images'))

        if uploaded.mimetype != 'image/webp':
            flash('Las imágenes hero deben ser WEBP', 'error')
            return redirect(url_for('admin.camping_hero_images'))

        object_name = minio_service.upload_file(uploaded, uploaded.mimetype)
        image_url = minio_service.get_file_url(object_name)
        if not image_url:
            flash('No se pudo subir a MinIO', 'error')
            return redirect(url_for('admin.camping_hero_images'))

        max_order = db.session.query(db.func.max(HeroImage.sort_order)).scalar() or 0
        
        new_hero = HeroImage(url=image_url, sort_order=max_order + 1, is_active=True)
        db.session.add(new_hero)
        db.session.flush()

        db.session.add(MediaAsset(
            object_name=object_name,
            url=image_url,
            mime_type='image/webp',
            size_bytes=uploaded.content_length or 0,
            usage_type='hero',
            reference_id=new_hero.id,
        ))

        db.session.commit()
        cache_service.clear_prefix("public_")
        log_activity('HERO_IMAGE_UPLOAD', f'Nueva imagen de portada subida: {object_name}')
        flash('Imagen de portada subida correctamente', 'success')
        return redirect(url_for('admin.camping_hero_images'))

    images = HeroImage.query.order_by(HeroImage.sort_order.asc(), HeroImage.id.desc()).all()
    return render_template('admin/camping_hero_images.html', images=images)


@admin_bp.route('/camping/hero-images/<int:image_id>/toggle', methods=['POST'])
@login_required
def toggle_hero_image(image_id):
    img = HeroImage.query.get_or_404(image_id)
    img.is_active = not img.is_active
    db.session.commit()
    cache_service.clear_prefix("public_")
    status = "activa" if img.is_active else "inactiva"
    log_activity('HERO_IMAGE_TOGGLE', f'Imagen hero {image_id} marcada como {status}')
    flash(f'Imagen marcada como {status}', 'success')
    return redirect(url_for('admin.camping_hero_images'))


@admin_bp.route('/camping/hero-images/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_hero_image(image_id):
    img = HeroImage.query.get_or_404(image_id)
    asset = MediaAsset.query.filter_by(url=img.url).first()
    if asset:
        minio_service.remove_object(asset.object_name)
        db.session.delete(asset)
    
    db.session.delete(img)
    db.session.commit()
    cache_service.clear_prefix("public_")
    log_activity('HERO_IMAGE_DELETE', f'Imagen hero {image_id} eliminada')
    flash('Imagen de portada eliminada', 'success')
    return redirect(url_for('admin.camping_hero_images'))
