from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.services.cache_service import cache_service
from app.models.camping import CampingService, ServiceImage, MediaAsset, Amenity
from app.utils.logging_helper import log_activity
from app.services.minio_service import minio_service
from .. import admin_bp

@admin_bp.route('/camping/services', methods=['GET', 'POST'])
@login_required
def camping_services():
    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)
        slug = (request.form.get('slug') or '').strip().lower()
        service_type = (request.form.get('service_type') or '').strip().lower()
        name_es = (request.form.get('name_es') or '').strip()
        name_en = (request.form.get('name_en') or '').strip()
        name_pt = (request.form.get('name_pt') or '').strip()
        description_es = (request.form.get('description_es') or '').strip()
        description_en = (request.form.get('description_en') or '').strip()
        description_pt = (request.form.get('description_pt') or '').strip()
        amenity_ids = request.form.getlist('amenity_ids', type=int)

        if not all([slug, service_type, name_es, name_en, name_pt, description_es, description_en, description_pt]):
            flash('Completa todos los campos obligatorios del servicio', 'error')
            return redirect(url_for('admin.camping_services'))

        service = CampingService.query.get(service_id) if service_id else CampingService()
        if not service:
            flash('Servicio no encontrado', 'error')
            return redirect(url_for('admin.camping_services'))

        service.slug = slug
        service.service_type = service_type
        service.name_es = name_es
        service.name_en = name_en
        service.name_pt = name_pt
        service.description_es = description_es
        service.description_en = description_en
        service.description_pt = description_pt
        service.price = request.form.get('price', type=int) or 0
        service.currency = (request.form.get('currency') or 'UYU').strip().upper()
        service.capacity = request.form.get('capacity', type=int) or 1
        service.total_units = request.form.get('total_units', type=int) or 0
        service.available_units = request.form.get('available_units', type=int) or 0
        service.is_featured = request.form.get('is_featured') == 'on'
        service.is_promo = request.form.get('is_promo') == 'on'
        service.is_active = request.form.get('is_active') == 'on'
        
        service.amenities = Amenity.query.filter(Amenity.id.in_(amenity_ids)).all()

        if not service_id:
            db.session.add(service)
            db.session.flush()

        uploaded_images = request.files.getlist('images')
        if uploaded_images:
            valid_images = [img for img in uploaded_images if img and img.filename]
            if len(valid_images) > 3:
                flash('Cada servicio admite hasta 3 imágenes', 'error')
                return redirect(url_for('admin.camping_services'))

            ServiceImage.query.filter_by(service_id=service.id).delete()
            for index, uploaded in enumerate(valid_images):
                if uploaded.mimetype != 'image/webp':
                    flash('Las imágenes del servicio deben ser WEBP', 'error')
                    return redirect(url_for('admin.camping_services'))

                object_name = minio_service.upload_file(uploaded, uploaded.mimetype)
                image_url = minio_service.get_file_url(object_name)
                if not image_url:
                    flash('No se pudo generar URL pública de MinIO', 'error')
                    return redirect(url_for('admin.camping_services'))

                db.session.add(ServiceImage(service_id=service.id, url=image_url, sort_order=index))
                db.session.add(MediaAsset(
                    object_name=object_name,
                    url=image_url,
                    mime_type='image/webp',
                    size_bytes=uploaded.content_length or 0,
                    usage_type='service',
                    reference_id=service.id,
                ))

        db.session.commit()
        cache_service.clear_prefix("public_")
        log_activity('SERVICE_UPSERT', f'Servicio guardado: {service.slug}')
        flash('Servicio guardado correctamente', 'success')
        return redirect(url_for('admin.camping_services'))

    all_services = CampingService.query.order_by(CampingService.created_at.desc()).all()
    all_amenities = Amenity.query.order_by(Amenity.name_es.asc()).all()
    return render_template('admin/camping_services.html', services=all_services, amenities=all_amenities)


@admin_bp.route('/camping/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_camping_service(service_id):
    service = CampingService.query.get_or_404(service_id)
    
    if request.method == 'POST':
        slug = (request.form.get('slug') or '').strip().lower()
        service_type = (request.form.get('service_type') or '').strip().lower()
        name_es = (request.form.get('name_es') or '').strip()
        name_en = (request.form.get('name_en') or '').strip()
        name_pt = (request.form.get('name_pt') or '').strip()
        description_es = (request.form.get('description_es') or '').strip()
        description_en = (request.form.get('description_en') or '').strip()
        description_pt = (request.form.get('description_pt') or '').strip()
        amenity_ids = request.form.getlist('amenity_ids', type=int)

        if not all([slug, service_type, name_es, name_en, name_pt, description_es, description_en, description_pt]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('admin.edit_camping_service', service_id=service.id))

        service.slug = slug
        service.service_type = service_type
        service.name_es = name_es
        service.name_en = name_en
        service.name_pt = name_pt
        service.description_es = description_es
        service.description_en = description_en
        service.description_pt = description_pt
        service.price = request.form.get('price', type=int) or 0
        service.currency = (request.form.get('currency') or 'UYU').strip().upper()
        service.capacity = request.form.get('capacity', type=int) or 1
        service.total_units = request.form.get('total_units', type=int) or 0
        service.available_units = request.form.get('available_units', type=int) or 0
        service.is_featured = request.form.get('is_featured') == 'on'
        service.is_promo = request.form.get('is_promo') == 'on'
        service.is_active = request.form.get('is_active') == 'on'
        
        service.amenities = Amenity.query.filter(Amenity.id.in_(amenity_ids)).all()

        db.session.add(service)

        uploaded_images = request.files.getlist('images')
        valid_images = [img for img in uploaded_images if img and img.filename]
        
        if valid_images:
            current_count = ServiceImage.query.filter_by(service_id=service.id).count()
            if (current_count + len(valid_images)) > 3:
                flash(f'El producto ya tiene {current_count} imágenes. Solo puedes subir {3 - current_count} más.', 'error')
                return redirect(url_for('admin.edit_camping_service', service_id=service.id))

            for index, uploaded in enumerate(valid_images):
                if uploaded.mimetype != 'image/webp':
                    flash('Las imágenes deben ser WEBP', 'error')
                    return redirect(url_for('admin.edit_camping_service', service_id=service.id))

                object_name = minio_service.upload_file(uploaded, uploaded.mimetype)
                image_url = minio_service.get_file_url(object_name)
                
                db.session.add(ServiceImage(service_id=service.id, url=image_url, sort_order=current_count + index))
                db.session.add(MediaAsset(
                    object_name=object_name,
                    url=image_url,
                    mime_type='image/webp',
                    size_bytes=uploaded.content_length or 0,
                    usage_type='service',
                    reference_id=service.id,
                ))

        db.session.commit()
        cache_service.clear_prefix("public_")
        log_activity('SERVICE_UPDATE', f'Servicio actualizado: {service.slug}')
        flash('Servicio actualizado correctamente', 'success')
        return redirect(url_for('admin.camping_services'))

    available_amenities = Amenity.query.order_by(Amenity.name_es.asc()).all()
    return render_template('admin/camping_service_edit.html', service=service, available_amenities=available_amenities)


@admin_bp.route('/camping/services/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_service_image(image_id):
    image = ServiceImage.query.get_or_404(image_id)
    service_id = image.service_id
    
    asset = MediaAsset.query.filter_by(url=image.url).first()
    if asset:
        minio_service.remove_object(asset.object_name)
        db.session.delete(asset)
    
    db.session.delete(image)
    db.session.commit()
    
    log_activity('SERVICE_IMAGE_DELETE', f'Imagen eliminada de servicio ID: {service_id}')
    flash('Imagen eliminada de la galería', 'success')
    return redirect(url_for('admin.edit_camping_service', service_id=service_id))


@admin_bp.route('/camping/services/<int:service_id>/delete', methods=['POST'])
@login_required
def delete_camping_service(service_id):
    service = CampingService.query.get_or_404(service_id)
    slug = service.slug
    db.session.delete(service)
    db.session.commit()
    cache_service.clear_prefix("public_")
    log_activity('SERVICE_DELETE', f'Servicio eliminado: {slug}')
    flash('Servicio eliminado', 'success')
    return redirect(url_for('admin.camping_services'))
