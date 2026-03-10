"""
API pÃºblica del Punto Violeta Digital.
Endpoints: contacto y localidades/puntos de referencia.
"""

from datetime import datetime, time, timedelta
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, func
from app.extensions import db, limiter
from app.models.violeta import ContactMessage, Locality, BlogPost, BlogCategory, Reading
from app.services.email_service import send_contact_confirmation_email

api_bp = Blueprint('api', __name__)

# Registrar rutas de autenticaciÃ³n (2FA para panel admin)
from . import auth  # noqa: F401, E402


# â”€â”€â”€ Formulario de Contacto â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_bp.route('/contact', methods=['POST'])
@limiter.limit("5 per minute")
def contact():
    """
    Recibe el formulario de contacto del frontend.
    Campos esperados (JSON):
      - name: str (opcional)
      - contactMethod: str (requerido)
      - safeTime: str (opcional)
      - message: str (requerido)
      - acknowledgedNoEmergency: bool (requerido en true)
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'message': 'JSON invÃ¡lido.'}), 400

    contact_method = (data.get('contactMethod') or '').strip()
    message_text = (data.get('message') or '').strip()
    acknowledged = data.get('acknowledgedNoEmergency', False)

    # Validaciones
    if not contact_method:
        return jsonify({'message': 'Por favor indicÃ¡ cÃ³mo contactarte.'}), 422
    if not message_text:
        return jsonify({'message': 'El mensaje no puede estar vacÃ­o.'}), 422
    if not acknowledged:
        return jsonify({'message': 'Debes confirmar que entendÃ©s que esto no es una lÃ­nea de emergencia.'}), 422

    msg = ContactMessage(
        name=(data.get('name') or '').strip() or None,
        contact_method=contact_method,
        safe_time=(data.get('safeTime') or '').strip() or None,
        message=message_text,
        acknowledged_no_emergency=bool(acknowledged),
        status=ContactMessage.STATUS_NEW,
    )
    db.session.add(msg)
    db.session.commit()

    # Enviar email de confirmaciÃ³n al mÃ©todo de contacto indicado (solo si parece un email)
    if '@' in contact_method:
        try:
            send_contact_confirmation_email(to_email=contact_method, msg=msg)
        except Exception:
            pass  # No bloqueamos la respuesta si el mail falla

    return jsonify({
        'message': 'Tu mensaje fue recibido. Intentaremos contactarte en el horario que indicaste.',
        'id': msg.id,
    }), 201


# â”€â”€â”€ Localidades y Puntos de Referencia â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_bp.route('/localities', methods=['GET'])
def public_localities():
    """Devuelve todas las localidades activas con sus puntos de referencia activos."""
    localities = Locality.query.filter_by(is_active=True).order_by(Locality.name.asc()).all()
    return jsonify([loc.to_dict() for loc in localities])


@api_bp.route('/localities/<int:locality_id>', methods=['GET'])
def public_locality_detail(locality_id):
    locality = Locality.query.filter_by(id=locality_id, is_active=True).first_or_404()
    return jsonify(locality.to_dict())


@api_bp.route('/blog/posts', methods=['GET'])
def public_blog_posts():
    """Devuelve posts publicados con paginación y búsqueda."""
    raw_query = (request.args.get('q') or '').strip()
    raw_category = (request.args.get('category') or '').strip()
    raw_date_from = (request.args.get('date_from') or '').strip()
    raw_date_to = (request.args.get('date_to') or '').strip()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    if page < 1:
        page = 1

    per_page = 20 if per_page is None else per_page
    per_page = max(1, min(per_page, 20))

    parsed_date_from = None
    parsed_date_to = None

    if raw_date_from:
        try:
            parsed_date_from = datetime.strptime(raw_date_from, '%Y-%m-%d')
        except ValueError:
            return jsonify({'message': 'La fecha desde es inválida.'}), 422

    if raw_date_to:
        try:
            parsed_date_to = datetime.strptime(raw_date_to, '%Y-%m-%d')
        except ValueError:
            return jsonify({'message': 'La fecha hasta es inválida.'}), 422

    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        return jsonify({'message': 'La fecha desde no puede ser mayor a la fecha hasta.'}), 422

    query = BlogPost.query.filter_by(status=BlogPost.STATUS_PUBLISHED)
    date_field = func.coalesce(BlogPost.published_at, BlogPost.created_at)

    if raw_query:
        search_term = f"%{raw_query}%"
        query = query.filter(
            or_(
                BlogPost.title.ilike(search_term),
                BlogPost.excerpt.ilike(search_term),
                BlogPost.content_html.ilike(search_term),
            )
        )

    if raw_category:
        query = query.join(BlogCategory, BlogPost.category_id == BlogCategory.id)
        query = query.filter(func.lower(BlogCategory.name) == raw_category.lower())

    if parsed_date_from:
        from_start = datetime.combine(parsed_date_from.date(), time.min)
        query = query.filter(date_field >= from_start)

    if parsed_date_to:
        to_end_exclusive = datetime.combine(parsed_date_to.date(), time.min) + timedelta(days=1)
        query = query.filter(date_field < to_end_exclusive)

    available_categories = [
        category_name
        for (category_name,) in (
            db.session.query(BlogCategory.name)
            .join(BlogPost, BlogPost.category_id == BlogCategory.id)
            .filter(BlogPost.status == BlogPost.STATUS_PUBLISHED)
            .filter(BlogCategory.name.isnot(None))
            .distinct()
            .order_by(BlogCategory.name.asc())
            .all()
        )
        if category_name
    ]

    pagination = query.order_by(
        BlogPost.published_at.desc(),
        BlogPost.created_at.desc(),
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [post.to_dict() for post in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_items': pagination.total,
            'total_pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        },
        'filters': {
            'category': raw_category,
            'date_from': raw_date_from,
            'date_to': raw_date_to,
        },
        'available_categories': available_categories,
        'query': raw_query,
    })


@api_bp.route('/blog/posts/<string:slug>', methods=['GET'])
def public_blog_post_detail(slug):
    """Devuelve detalle de un post publicado por slug."""
    post = BlogPost.query.filter_by(
        slug=slug,
        status=BlogPost.STATUS_PUBLISHED,
    ).first_or_404()

    related_posts = (
        BlogPost.query
        .filter(
            BlogPost.status == BlogPost.STATUS_PUBLISHED,
            BlogPost.id != post.id,
        )
        .order_by(BlogPost.published_at.desc(), BlogPost.created_at.desc())
        .limit(3)
        .all()
    )

    post_payload = post.to_dict()
    post_payload['content_html'] = post.content_html

    return jsonify({
        'item': post_payload,
        'related': [related.to_dict() for related in related_posts],
    })


@api_bp.route('/readings', methods=['GET'])
def public_readings():
    """Devuelve lecturas activas con paginación para el frontend."""
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=12, type=int)

    if page < 1:
        page = 1

    per_page = 12 if per_page is None else per_page
    per_page = max(1, min(per_page, 24))

    query = Reading.query.filter_by(is_active=True)
    pagination = query.order_by(Reading.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return jsonify({
        'items': [reading.to_dict() for reading in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_items': pagination.total,
            'total_pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        },
    })


# â”€â”€â”€ Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_bp.route('/health', methods=['GET'])
def api_health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})




