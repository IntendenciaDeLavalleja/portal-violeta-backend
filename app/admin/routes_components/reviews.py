from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.services.cache_service import cache_service
from app.models.camping import CampingService, ServiceTestimonial, MediaAsset
from app.utils.logging_helper import log_activity
from app.services.minio_service import minio_service
from .. import admin_bp

@admin_bp.route('/camping/reviews', methods=['GET', 'POST'])
@admin_bp.route('/camping/testimonios', methods=['GET', 'POST'])
@login_required
def camping_testimonials():
    if request.method == 'POST':
        testimonial_id = request.form.get('testimonial_id', type=int)
        testimonial = ServiceTestimonial.query.get(testimonial_id) if testimonial_id else ServiceTestimonial()
        if not testimonial:
            flash('Testimonio no encontrado', 'error')
            return redirect(url_for('admin.camping_testimonials'))

        testimonial.author_name = (request.form.get('author_name') or '').strip()
        testimonial.comment_es = (request.form.get('comment_es') or '').strip()
        testimonial.comment_en = (request.form.get('comment_en') or '').strip()
        testimonial.comment_pt = (request.form.get('comment_pt') or '').strip()
        testimonial.is_published = request.form.get('is_published') == 'on'
        testimonial.service_id = request.form.get('service_id', type=int)

        if not all([testimonial.author_name, testimonial.comment_es, testimonial.comment_en, testimonial.comment_pt]):
            flash('Completa nombre y comentarios en los 3 idiomas', 'error')
            return redirect(url_for('admin.camping_testimonials'))

        if not testimonial_id:
            db.session.add(testimonial)
            db.session.flush()

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            if image_file.mimetype != 'image/webp':
                flash('La imagen del testimonio debe ser WEBP', 'error')
                return redirect(url_for('admin.camping_testimonials'))

            object_name = minio_service.upload_file(image_file, image_file.mimetype)
            image_url = minio_service.get_file_url(object_name)
            testimonial.image_url = image_url
            db.session.add(MediaAsset(
                object_name=object_name,
                url=image_url,
                mime_type='image/webp',
                size_bytes=image_file.content_length or 0,
                usage_type='testimonial',
                reference_id=testimonial.id,
            ))

        db.session.commit()
        cache_service.clear_prefix("public_")
        log_activity('TESTIMONIAL_UPSERT', f'Testimonio guardado ID {testimonial.id}')
        flash('Testimonio guardado', 'success')
        return redirect(url_for('admin.camping_testimonials'))

    testimonials_list = ServiceTestimonial.query.order_by(ServiceTestimonial.created_at.desc()).all()
    services_list = CampingService.query.order_by(CampingService.name_es.asc()).all()
    return render_template('admin/camping_reviews.html', testimonials=testimonials_list, services=services_list)


@admin_bp.route('/camping/reviews/<int:testimonial_id>/edit', methods=['GET', 'POST'])
@admin_bp.route('/camping/testimonios/<int:testimonial_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_camping_testimonial(testimonial_id):
    testimonial = ServiceTestimonial.query.get_or_404(testimonial_id)
    
    if request.method == 'POST':
        testimonial.author_name = (request.form.get('author_name') or '').strip()
        testimonial.comment_es = (request.form.get('comment_es') or '').strip()
        testimonial.comment_en = (request.form.get('comment_en') or '').strip()
        testimonial.comment_pt = (request.form.get('comment_pt') or '').strip()
        testimonial.is_published = request.form.get('is_published') == 'on'
        testimonial.service_id = request.form.get('service_id', type=int) or None

        if not all([testimonial.author_name, testimonial.comment_es, testimonial.comment_en, testimonial.comment_pt]):
            flash('Completa nombre y comentarios en los 3 idiomas', 'error')
            return redirect(url_for('admin.edit_camping_testimonial', testimonial_id=testimonial.id))

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            if image_file.mimetype != 'image/webp':
                flash('La imagen del testimonio debe ser WEBP', 'error')
                return redirect(url_for('admin.edit_camping_testimonial', testimonial_id=testimonial.id))

            if testimonial.image_url:
                old_asset = MediaAsset.query.filter_by(url=testimonial.image_url).first()
                if old_asset:
                    minio_service.remove_object(old_asset.object_name)
                    db.session.delete(old_asset)

            object_name = minio_service.upload_file(image_file, image_file.mimetype)
            image_url = minio_service.get_file_url(object_name)
            testimonial.image_url = image_url
            db.session.add(MediaAsset(
                object_name=object_name,
                url=image_url,
                mime_type='image/webp',
                size_bytes=image_file.content_length or 0,
                usage_type='testimonial',
                reference_id=testimonial.id,
            ))

        db.session.commit()
        cache_service.clear_prefix("public_")
        log_activity('TESTIMONIAL_UPDATE', f'Testimonio actualizado ID {testimonial.id}')
        flash('Testimonio actualizado correctamente', 'success')
        return redirect(url_for('admin.camping_testimonials'))

    services_list = CampingService.query.order_by(CampingService.name_es.asc()).all()
    return render_template('admin/camping_review_edit.html', testimonial=testimonial, services=services_list)


@admin_bp.route('/camping/reviews/<int:testimonial_id>/delete', methods=['POST'])
@admin_bp.route('/camping/testimonios/<int:testimonial_id>/delete', methods=['POST'])
@login_required
def delete_camping_testimonial(testimonial_id):
    testimonial = ServiceTestimonial.query.get_or_404(testimonial_id)
    db.session.delete(testimonial)
    db.session.commit()
    cache_service.clear_prefix("public_")

    log_activity('TESTIMONIAL_DELETE', f'Testimonio eliminado ID {testimonial_id}')
    flash('Testimonio eliminado', 'success')
    return redirect(url_for('admin.camping_testimonials'))
