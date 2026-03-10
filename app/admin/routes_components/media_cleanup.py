from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.camping import HeroImage, ServiceImage, ServiceTestimonial, MediaAsset
from app.utils.logging_helper import log_activity
from app.services.minio_service import minio_service
from .. import admin_bp

@admin_bp.route('/camping/media-cleanup', methods=['GET', 'POST'])
@login_required
def camping_media_cleanup():
    if request.method == 'POST':
        object_name = (request.form.get('object_name') or '').strip()
        if not object_name:
            flash('Objeto inválido', 'error')
            return redirect(url_for('admin.camping_media_cleanup'))

        if minio_service.remove_object(object_name):
            MediaAsset.query.filter_by(object_name=object_name).delete()
            db.session.commit()
            log_activity('MEDIA_DELETE', f'Objeto MinIO eliminado: {object_name}')
            flash('Imagen eliminada de MinIO', 'success')
        else:
            flash('No se pudo eliminar el objeto en MinIO', 'error')

        return redirect(url_for('admin.camping_media_cleanup'))

    referenced_urls = set()
    referenced_urls.update([img.url for img in HeroImage.query.all()])
    referenced_urls.update([img.url for img in ServiceImage.query.all()])
    referenced_urls.update([rev.image_url for rev in ServiceTestimonial.query.filter(ServiceTestimonial.image_url.isnot(None)).all()])

    assets = MediaAsset.query.order_by(MediaAsset.created_at.desc()).all()
    orphan_assets = [asset for asset in assets if asset.url not in referenced_urls]

    return render_template('admin/camping_media_cleanup.html', orphan_assets=orphan_assets, total_assets=len(assets))
