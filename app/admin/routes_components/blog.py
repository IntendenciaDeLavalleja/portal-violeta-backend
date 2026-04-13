"""Gestión completa del Blog del Punto Violeta Digital."""

import re
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.violeta import BlogPost, BlogCategory, BlogAuthor
from app.utils.logging_helper import log_activity
from .. import admin_bp


_BLOG_POST_LIMITS = {
    'title': 300,
    'slug': 350,
    'excerpt': 600,
    'cover_image_url': 600,
    'cover_image_key': 300,
}

_SLUG_SEPARATOR_RE = re.compile(
    r'[\s_\-\u2010\u2011\u2012\u2013\u2014\u2015]+'
)
_SLUG_ALLOWED_CHARS_RE = re.compile(
    r'[^a-z0-9\s_\-\u2010\u2011\u2012\u2013\u2014\u2015]'
)


def _slugify(text: str) -> str:
    """Genera un slug URL-seguro a partir de un texto."""
    text = text.lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'ñ', 'n', text)
    text = _SLUG_ALLOWED_CHARS_RE.sub('', text)
    text = _SLUG_SEPARATOR_RE.sub('-', text)
    return text.strip('-')


def _unique_post_slug(base: str, exclude_id: int = None) -> str:
    slug = base
    counter = 1
    while True:
        query = BlogPost.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(BlogPost.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _unique_category_slug(base: str, exclude_id: int = None) -> str:
    slug = base
    counter = 1
    while True:
        query = BlogCategory.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(BlogCategory.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _build_form_data(source, post=None):
    return {
        'title': source.get('title', post.title if post else ''),
        'slug': source.get('slug', post.slug if post else ''),
        'content_html': source.get('content_html', post.content_html if post else ''),
        'excerpt': source.get('excerpt', post.excerpt if post else ''),
        'cover_image_url': source.get('cover_image_url', post.cover_image_url if post else ''),
        'cover_image_key': source.get('cover_image_key', post.cover_image_key if post else ''),
        'category_id': source.get('category_id', str(post.category_id) if post and post.category_id else ''),
        'blog_author_id': source.get('blog_author_id', str(post.blog_author_id) if post and post.blog_author_id else ''),
    }


def _validate_post_lengths(form_data: dict):
    checks = [
        ('title', 'El título'),
        ('slug', 'El slug'),
        ('excerpt', 'El resumen/extracto'),
        ('cover_image_url', 'La URL de portada'),
        ('cover_image_key', 'La clave de portada'),
    ]

    for field_name, label in checks:
        value = (form_data.get(field_name) or '').strip()
        limit = _BLOG_POST_LIMITS[field_name]
        if value and len(value) > limit:
            return (
                f'{label} supera el máximo de {limit} caracteres '
                f'({len(value)} enviados).'
            )

    return None


def _parse_category_id(raw_category_id: str):
    try:
        category_id = int((raw_category_id or '').strip())
    except (TypeError, ValueError):
        return None

    return BlogCategory.query.get(category_id)


@admin_bp.route('/blog')
@login_required
def blog_posts():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog_posts.html', posts=posts)


@admin_bp.route('/blog/categories', methods=['GET', 'POST'])
@login_required
def blog_categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip() or None
        is_active = bool(request.form.get('is_active'))

        if not name:
            flash('El nombre de la categoría es obligatorio.', 'error')
            categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
            return render_template('admin/blog_categories.html', categories=categories)

        if not description:
            flash('La descripción de la categoría es obligatoria.', 'error')
            categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
            return render_template('admin/blog_categories.html', categories=categories)

        base_slug = _slugify(name)
        if not base_slug:
            flash('El nombre de la categoría no es válido.', 'error')
            categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
            return render_template('admin/blog_categories.html', categories=categories)

        category = BlogCategory(
            name=name,
            slug=_unique_category_slug(base_slug),
            description=description,
            is_active=is_active,
        )
        db.session.add(category)
        db.session.commit()
        log_activity('BLOG_CATEGORY_CREATE', f'Categoría creada: "{category.name}"')
        flash(f'Categoría "{category.name}" creada.', 'success')
        return redirect(url_for('admin.blog_categories'))

    categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
    return render_template('admin/blog_categories.html', categories=categories)


@admin_bp.route('/blog/categories/<int:category_id>/update', methods=['POST'])
@login_required
def blog_category_update(category_id):
    category = BlogCategory.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip() or None
    is_active = bool(request.form.get('is_active'))

    if not name:
        flash('El nombre de la categoría es obligatorio.', 'error')
        return redirect(url_for('admin.blog_categories'))

    if not description:
        flash('La descripción de la categoría es obligatoria.', 'error')
        return redirect(url_for('admin.blog_categories'))

    base_slug = _slugify(name)
    if not base_slug:
        flash('El nombre de la categoría no es válido.', 'error')
        return redirect(url_for('admin.blog_categories'))

    category.name = name
    category.slug = _unique_category_slug(base_slug, exclude_id=category.id)
    category.description = description
    category.is_active = is_active

    db.session.commit()
    log_activity('BLOG_CATEGORY_EDIT', f'Categoría editada: "{category.name}"')
    flash(f'Categoría "{category.name}" actualizada.', 'success')
    return redirect(url_for('admin.blog_categories'))


@admin_bp.route('/blog/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def blog_category_delete(category_id):
    category = BlogCategory.query.get_or_404(category_id)
    linked_posts = BlogPost.query.filter_by(category_id=category.id).count()
    if linked_posts > 0:
        flash('No se puede eliminar una categoría con entradas asociadas.', 'error')
        return redirect(url_for('admin.blog_categories'))

    category_name = category.name
    db.session.delete(category)
    db.session.commit()
    log_activity('BLOG_CATEGORY_DELETE', f'Categoría eliminada: "{category_name}"')
    flash(f'Categoría "{category_name}" eliminada.', 'success')
    return redirect(url_for('admin.blog_categories'))


@admin_bp.route('/blog/new', methods=['GET', 'POST'])
@login_required
def blog_post_new():
    categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
    if not categories:
        flash('Primero creá al menos una categoría para poder publicar entradas.', 'info')
        return redirect(url_for('admin.blog_categories'))

    authors = BlogAuthor.query.filter_by(is_active=True).order_by(BlogAuthor.name.asc()).all()

    if request.method == 'POST':
        form_data = _build_form_data(request.form)
        length_error = _validate_post_lengths(form_data)
        if length_error:
            flash(length_error, 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        title = form_data['title'].strip()
        raw_slug = form_data['slug'].strip()
        content_html = form_data['content_html'].strip()
        excerpt = form_data['excerpt'].strip()
        cover_image_url = form_data['cover_image_url'].strip()
        cover_image_key = form_data['cover_image_key'].strip()
        category = _parse_category_id(form_data['category_id'])
        action = request.form.get('action', 'draft')   # 'draft' | 'publish'

        if action not in {'draft', 'publish'}:
            flash('Acción de publicación inválida.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        if category is None:
            flash('Seleccioná una categoría válida.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        if not title:
            flash('El título es obligatorio.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        if not content_html:
            flash('El contenido no puede estar vacío.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        if not excerpt:
            flash('El resumen/extracto es obligatorio.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        if not cover_image_url or not cover_image_key:
            flash('La imagen de portada es obligatoria.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        base_slug = _slugify(raw_slug or title)
        if not base_slug:
            flash('El slug generado no es válido. Revisá título/slug.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        try:
            blog_author_id = int(form_data.get('blog_author_id') or 0) or None
        except (TypeError, ValueError):
            blog_author_id = None

        if not blog_author_id:
            flash('Debes seleccionar una autora/or.', 'error')
            return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data=form_data)

        slug = _unique_post_slug(base_slug)
        status = BlogPost.STATUS_PUBLISHED if action == 'publish' else BlogPost.STATUS_DRAFT

        post = BlogPost(
            title=title,
            slug=slug,
            category_id=category.id,
            content_html=content_html,
            excerpt=excerpt or None,
            cover_image_url=cover_image_url or None,
            cover_image_key=cover_image_key or None,
            blog_author_id=blog_author_id,
            status=status,
            author_id=current_user.id,
            published_at=datetime.utcnow() if status == BlogPost.STATUS_PUBLISHED else None,
        )
        db.session.add(post)
        db.session.commit()
        log_activity('BLOG_POST_CREATE', f'Post creado: "{post.title}" [{post.status}]')
        flash(f'Post "{post.title}" creado como {status}.', 'success')
        return redirect(url_for('admin.blog_posts'))

    return render_template('admin/blog_post_edit.html', post=None, categories=categories, authors=authors, form_data={})


@admin_bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def blog_post_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)
    categories = BlogCategory.query.order_by(BlogCategory.name.asc()).all()
    authors = BlogAuthor.query.filter_by(is_active=True).order_by(BlogAuthor.name.asc()).all()

    if not categories:
        flash('Primero creá al menos una categoría para poder editar entradas.', 'info')
        return redirect(url_for('admin.blog_categories'))

    if request.method == 'POST':
        form_data = _build_form_data(request.form, post=post)
        length_error = _validate_post_lengths(form_data)
        if length_error:
            flash(length_error, 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        category = _parse_category_id(form_data['category_id'])
        post.title = form_data['title'].strip()
        post.content_html = form_data['content_html'].strip()
        post.excerpt = form_data['excerpt'].strip() or None

        # Portada MinIO
        new_cover_url = form_data['cover_image_url'].strip()
        new_cover_key = form_data['cover_image_key'].strip()
        if not new_cover_url or not new_cover_key:
            flash('La imagen de portada es obligatoria.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        if new_cover_key != post.cover_image_key:
            # Eliminar portada anterior de MinIO si existía
            from app.services.minio_service import minio_service
            if post.cover_image_key:
                minio_service.remove_object(post.cover_image_key)
            post.cover_image_url = new_cover_url
            post.cover_image_key = new_cover_key

        # Autora/or
        try:
            post.blog_author_id = int(form_data.get('blog_author_id') or 0) or None
        except (TypeError, ValueError):
            post.blog_author_id = None

        action = request.form.get('action', 'draft')
        if action not in {'draft', 'publish'}:
            flash('Acción de publicación inválida.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        if category is None:
            flash('Seleccioná una categoría válida.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        post.category_id = category.id

        if not post.title:
            flash('El título es obligatorio.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        if not post.content_html:
            flash('El contenido no puede estar vacío.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        if not post.excerpt:
            flash('El resumen/extracto es obligatorio.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        if not post.blog_author_id:
            flash('Debes seleccionar una autora/or.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)

        new_base = _slugify((form_data['slug'] or '').strip() or post.title)
        if not new_base:
            flash('El slug ingresado no es válido.', 'error')
            return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=form_data)
        post.slug = _unique_post_slug(new_base, exclude_id=post.id)

        if action == 'publish' and post.status != BlogPost.STATUS_PUBLISHED:
            post.status = BlogPost.STATUS_PUBLISHED
            post.published_at = datetime.utcnow()
        elif action == 'draft':
            post.status = BlogPost.STATUS_DRAFT

        db.session.commit()
        log_activity('BLOG_POST_EDIT', f'Post editado: "{post.title}"')
        flash(f'Post "{post.title}" actualizado.', 'success')
        return redirect(url_for('admin.blog_posts'))

    return render_template('admin/blog_post_edit.html', post=post, categories=categories, authors=authors, form_data=_build_form_data({}, post=post))


@admin_bp.route('/blog/<int:post_id>/preview')
@login_required
def blog_post_preview(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return render_template('admin/blog_post_preview.html', post=post)


@admin_bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def blog_post_delete(post_id):
    post = BlogPost.query.get_or_404(post_id)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    log_activity('BLOG_POST_DELETE', f'Post eliminado: "{title}"')
    flash(f'Post "{title}" eliminado.', 'success')
    return redirect(url_for('admin.blog_posts'))
