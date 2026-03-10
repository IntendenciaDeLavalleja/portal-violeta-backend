"""
Gestión de Lecturas (documentos y recursos externos) del Punto Violeta Digital.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from urllib.parse import urlparse
from app.extensions import db
from app.models.violeta import Reading
from app.utils.logging_helper import log_activity
from .. import admin_bp


def _is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


@admin_bp.route('/readings')
@login_required
def readings():
    readings_list = Reading.query.order_by(Reading.created_at.desc()).all()
    return render_template('admin/readings.html', readings=readings_list)


@admin_bp.route('/readings/new', methods=['GET', 'POST'])
@login_required
def reading_new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        document_url = request.form.get('document_url', '').strip()
        cover_image_url = request.form.get('cover_image_url', '').strip()
        summary = request.form.get('summary', '').strip()

        if not title or not document_url:
            flash('Título y URL del documento son obligatorios.', 'error')
            return render_template('admin/reading_edit.html', reading=None)

        if not _is_valid_http_url(document_url):
            flash('La URL del documento no es válida (debe iniciar con http/https).', 'error')
            return render_template('admin/reading_edit.html', reading=None)

        if cover_image_url and not _is_valid_http_url(cover_image_url):
            flash('La URL de portada no es válida (debe iniciar con http/https).', 'error')
            return render_template('admin/reading_edit.html', reading=None)

        reading = Reading(
            title=title,
            document_url=document_url,
            cover_image_url=cover_image_url or None,
            summary=summary or None,
            is_active=bool(request.form.get('is_active')),
        )
        db.session.add(reading)
        db.session.commit()
        log_activity('READING_CREATE', f'Lectura creada: "{reading.title}"')
        flash(f'Lectura "{reading.title}" creada exitosamente.', 'success')
        return redirect(url_for('admin.readings'))

    return render_template('admin/reading_edit.html', reading=None)


@admin_bp.route('/readings/<int:reading_id>/edit', methods=['GET', 'POST'])
@login_required
def reading_edit(reading_id):
    reading = Reading.query.get_or_404(reading_id)

    if request.method == 'POST':
        reading.title = request.form.get('title', '').strip()
        reading.document_url = request.form.get('document_url', '').strip()
        reading.cover_image_url = request.form.get('cover_image_url', '').strip() or None
        reading.summary = request.form.get('summary', '').strip() or None
        reading.is_active = bool(request.form.get('is_active'))

        if not reading.title or not reading.document_url:
            flash('Título y URL del documento son obligatorios.', 'error')
            return render_template('admin/reading_edit.html', reading=reading)

        if not _is_valid_http_url(reading.document_url):
            flash('La URL del documento no es válida (debe iniciar con http/https).', 'error')
            return render_template('admin/reading_edit.html', reading=reading)

        if reading.cover_image_url and not _is_valid_http_url(reading.cover_image_url):
            flash('La URL de portada no es válida (debe iniciar con http/https).', 'error')
            return render_template('admin/reading_edit.html', reading=reading)

        db.session.commit()
        log_activity('READING_EDIT', f'Lectura editada: "{reading.title}"')
        flash(f'Lectura "{reading.title}" actualizada.', 'success')
        return redirect(url_for('admin.readings'))

    return render_template('admin/reading_edit.html', reading=reading)


@admin_bp.route('/readings/<int:reading_id>/delete', methods=['POST'])
@login_required
def reading_delete(reading_id):
    reading = Reading.query.get_or_404(reading_id)
    title = reading.title
    db.session.delete(reading)
    db.session.commit()
    log_activity('READING_DELETE', f'Lectura eliminada: "{title}"')
    flash(f'Lectura "{title}" eliminada.', 'success')
    return redirect(url_for('admin.readings'))
