"""Gestión de Autoras/es del Blog — CRUD completo."""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.extensions import db
from app.models.violeta import BlogAuthor, BlogPost
from app.services.minio_service import minio_service
from app.utils.logging_helper import log_activity
from .. import admin_bp


# ─── Listado + creación ───────────────────────────────────────────────────────

@admin_bp.route('/blog/authors')
@login_required
def blog_authors():
    authors = BlogAuthor.query.order_by(BlogAuthor.name.asc()).all()
    for author in authors:
        if author.photo_key:
            author.resolved_photo_url = minio_service.get_file_url(
                author.photo_key
            )
        else:
            author.resolved_photo_url = author.photo_url
    return render_template('admin/blog_authors.html', authors=authors)


@admin_bp.route('/blog/authors/new', methods=['POST'])
@login_required
def blog_author_create():
    name = request.form.get('name', '').strip()
    bio = request.form.get('bio', '').strip() or None
    photo_key = request.form.get('photo_key', '').strip() or None
    contact = request.form.get('contact', '').strip() or None
    is_active = bool(request.form.get('is_active'))

    if not photo_key:
        flash(
            'Debes subir una foto de perfil antes de crear la autora/or.',
            'error',
        )
        return redirect(url_for('admin.blog_authors'))

    photo_url = minio_service.get_file_url(photo_key)

    if not name:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('admin.blog_authors'))

    author = BlogAuthor(
        name=name, bio=bio,
        photo_url=photo_url, photo_key=photo_key,
        contact=contact, is_active=is_active,
    )
    db.session.add(author)
    db.session.commit()
    log_activity('BLOG_AUTHOR_CREATE', f'Autora/or creada/o: "{name}"')
    flash(f'Autora/or "{name}" creada/o correctamente.', 'success')
    return redirect(url_for('admin.blog_authors'))


# ─── Actualización ────────────────────────────────────────────────────────────

@admin_bp.route('/blog/authors/<int:author_id>/update', methods=['POST'])
@login_required
def blog_author_update(author_id):
    author = BlogAuthor.query.get_or_404(author_id)

    name = request.form.get('name', '').strip()
    if not name:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('admin.blog_authors'))

    author.name = name
    author.bio = request.form.get('bio', '').strip() or None
    author.contact = request.form.get('contact', '').strip() or None
    author.is_active = bool(request.form.get('is_active'))

    new_url = request.form.get('photo_url', '').strip() or None
    new_key = request.form.get('photo_key', '').strip() or None

    if not author.photo_key and not new_key and not new_url:
        flash(
            'Esta autora/or no tiene foto: sube una imagen para guardarla.',
            'error',
        )
        return redirect(url_for('admin.blog_authors'))

    # Sincronizar siempre URL+key de la foto con MinIO.
    if new_key:
        if new_key != author.photo_key and author.photo_key:
            minio_service.remove_object(author.photo_key)
        author.photo_key = new_key
        author.photo_url = minio_service.get_file_url(new_key)
    else:
        if author.photo_key:
            minio_service.remove_object(author.photo_key)
        author.photo_key = None
        author.photo_url = new_url

    db.session.commit()
    log_activity('BLOG_AUTHOR_UPDATE', f'Autora/or actualizada/o: "{author.name}"')
    flash(f'Autora/or "{author.name}" actualizada/o.', 'success')
    return redirect(url_for('admin.blog_authors'))


# ─── Eliminación ──────────────────────────────────────────────────────────────

@admin_bp.route('/blog/authors/<int:author_id>/delete', methods=['POST'])
@login_required
def blog_author_delete(author_id):
    author = BlogAuthor.query.get_or_404(author_id)

    linked = BlogPost.query.filter_by(blog_author_id=author.id).count()
    if linked > 0:
        flash(
            f'No se puede eliminar: "{author.name}" tiene {linked} '
            f'{"entrada" if linked == 1 else "entradas"} asociada{"" if linked == 1 else "s"}.',
            'error',
        )
        return redirect(url_for('admin.blog_authors'))

    if author.photo_key:
        minio_service.remove_object(author.photo_key)

    name = author.name
    db.session.delete(author)
    db.session.commit()
    log_activity('BLOG_AUTHOR_DELETE', f'Autora/or eliminada/o: "{name}"')
    flash(f'Autora/or "{name}" eliminada/o.', 'success')
    return redirect(url_for('admin.blog_authors'))
