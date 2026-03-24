"""
Rutas principales del panel de administración del Punto Violeta Digital.
"""
from flask import render_template
from flask_login import login_required
from app.models.violeta import Locality, ReferencePoint, BlogPost, Reading, ContactMessage
from . import admin_bp

# ─── Módulos de rutas ──────────────────────────────────────────────────────────
from .routes_components import auth        # noqa: F401
from .routes_components import audit       # noqa: F401
from .routes_components import localities  # noqa: F401
from .routes_components import blog        # noqa: F401
from .routes_components import blog_authors  # noqa: F401
from .routes_components import uploads     # noqa: F401
from .routes_components import readings    # noqa: F401
from .routes_components import messages    # noqa: F401


@admin_bp.route('/')
@login_required
def dashboard():
    # Estadísticas para el dashboard
    total_localities = Locality.query.count()
    active_localities = Locality.query.filter_by(is_active=True).count()
    total_points = ReferencePoint.query.count()
    active_points = ReferencePoint.query.filter_by(is_active=True).count()

    total_posts = BlogPost.query.count()
    published_posts = BlogPost.query.filter_by(status=BlogPost.STATUS_PUBLISHED).count()
    draft_posts = BlogPost.query.filter_by(status=BlogPost.STATUS_DRAFT).count()

    total_readings = Reading.query.count()
    active_readings = Reading.query.filter_by(is_active=True).count()

    new_messages = ContactMessage.query.filter_by(status=ContactMessage.STATUS_NEW).count()
    total_messages = ContactMessage.query.count()

    recent_messages = (
        ContactMessage.query
        .filter_by(status=ContactMessage.STATUS_NEW)
        .order_by(ContactMessage.created_at.desc())
        .limit(5).all()
    )
    recent_posts = (
        BlogPost.query
        .order_by(BlogPost.created_at.desc())
        .limit(5).all()
    )

    return render_template(
        'admin/dashboard.html',
        total_localities=total_localities,
        active_localities=active_localities,
        total_points=total_points,
        active_points=active_points,
        total_posts=total_posts,
        published_posts=published_posts,
        draft_posts=draft_posts,
        total_readings=total_readings,
        active_readings=active_readings,
        new_messages=new_messages,
        total_messages=total_messages,
        recent_messages=recent_messages,
        recent_posts=recent_posts,
    )
