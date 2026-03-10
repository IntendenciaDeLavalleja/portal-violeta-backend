"""
Modelos de datos para Punto Violeta Digital.
Incluye: Localidades, Puntos de Referencia, Posts del Blog, Lecturas y Mensajes de Contacto.
"""

from datetime import datetime
from app.extensions import db


class Locality(db.Model):
    __tablename__ = 'localities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    department = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reference_points = db.relationship(
        'ReferencePoint',
        backref='locality',
        cascade='all, delete-orphan',
        lazy='dynamic',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'description': self.description,
            'is_active': self.is_active,
            'reference_points': [rp.to_public_dict() for rp in self.reference_points.filter_by(is_active=True).all()],
        }

    def __repr__(self):
        return f'<Locality {self.name}>'


class ReferencePoint(db.Model):
    """Punto de referencia o recurso disponible dentro de una localidad."""
    __tablename__ = 'reference_points'

    CATEGORIES = [
        ('policia', 'Policía / Comisaría'),
        ('salud', 'Centro de Salud'),
        ('mides', 'MIDES / Servicios Sociales'),
        ('juridico', 'Asesoramiento Jurídico'),
        ('refugio', 'Refugio / Alojamiento'),
        ('apoyo', 'Centro de Apoyo'),
        ('otro', 'Otro'),
    ]

    id = db.Column(db.Integer, primary_key=True)
    locality_id = db.Column(db.Integer, db.ForeignKey('localities.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='otro')
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(60), nullable=True)
    whatsapp = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    schedule = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_public_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'address': self.address,
            'phone': self.phone,
            'whatsapp': self.whatsapp,
            'email': self.email,
            'description': self.description,
            'schedule': self.schedule,
            'latitude': self.latitude,
            'longitude': self.longitude,
        }

    def __repr__(self):
        return f'<ReferencePoint {self.name} ({self.locality.name if self.locality else "?"})>'


class BlogCategory(db.Model):
    __tablename__ = 'blog_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    description = db.Column(db.String(400), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BlogCategory {self.slug}>'


class BlogAuthor(db.Model):
    """Autor/a de entradas del Blog (independiente del usuario admin)."""
    __tablename__ = 'blog_authors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(600), nullable=True)   # URL pública completa
    photo_key = db.Column(db.String(300), nullable=True)   # Clave MinIO para eliminación
    contact = db.Column(db.String(300), nullable=True)     # Email o link red social
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'bio': self.bio,
            'photo_url': self.photo_url,
            'contact': self.contact,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<BlogAuthor {self.name}>'


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(350), nullable=False, unique=True, index=True)
    cover_image_url = db.Column(db.String(600), nullable=True)   # URL pública completa
    cover_image_key = db.Column(db.String(300), nullable=True)   # Clave MinIO para eliminación
    content_html = db.Column(db.Text, nullable=False, default='')
    excerpt = db.Column(db.String(600), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('blog_categories.id'), nullable=True, index=True)
    blog_author_id = db.Column(db.Integer, db.ForeignKey('blog_authors.id'), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    author_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('AdminUser', backref=db.backref('blog_posts', lazy='dynamic'))
    category = db.relationship('BlogCategory', backref=db.backref('posts', lazy='dynamic'))
    blog_author = db.relationship('BlogAuthor', backref=db.backref('posts', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'category': self.category.name if self.category else None,
            'cover_image_url': self.cover_image_url,
            'excerpt': self.excerpt,
            'author': self.blog_author.to_dict() if self.blog_author else None,
            'status': self.status,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<BlogPost {self.slug} [{self.status}]>'


class Reading(db.Model):
    """Documento/lectura recomendada con enlace externo."""
    __tablename__ = 'readings'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    document_url = db.Column(db.String(800), nullable=False)
    cover_image_url = db.Column(db.String(600), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'document_url': self.document_url,
            'cover_image_url': self.cover_image_url,
            'summary': self.summary,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Reading {self.title}>'


class ContactMessage(db.Model):
    """Mensaje enviado desde el formulario de contacto del frontend."""
    __tablename__ = 'contact_messages'

    STATUS_NEW = 'nuevo'
    STATUS_READ = 'leído'
    STATUS_REPLIED = 'respondido'
    STATUS_ARCHIVED = 'archivado'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)   # Opcional (alias)
    contact_method = db.Column(db.String(300), nullable=False)
    safe_time = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    acknowledged_no_emergency = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='nuevo')
    notes = db.Column(db.Text, nullable=True)   # Notas internas del admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage #{self.id} [{self.status}]>'
