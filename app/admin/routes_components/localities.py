"""
Gestion de Localidades y Puntos de Referencia para el Punto Violeta Digital.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.violeta import Locality, ReferencePoint
from app.utils.logging_helper import log_activity
from .. import admin_bp


def _parse_optional_coordinate(value, min_value, max_value):
    raw = (value or '').strip()
    if raw == '':
        return None
    parsed = float(raw)
    if parsed < min_value or parsed > max_value:
        raise ValueError(f'La coordenada debe estar entre {min_value} y {max_value}.')
    return parsed


def _opt(value):
    """Convierte un valor de formulario a None si está vacío o es la cadena 'None'."""
    v = (value or '').strip()
    return None if (v == '' or v.lower() == 'none') else v


# --- LOCALIDADES ---

@admin_bp.route('/localities')
@login_required
def localities():
    localities_list = Locality.query.order_by(Locality.name.asc()).all()
    return render_template('admin/localities.html', localities=localities_list)


@admin_bp.route('/localities/new', methods=['GET', 'POST'])
@login_required
def locality_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('El nombre es obligatorio.', 'error')
            return render_template('admin/locality_edit.html', locality=None)

        if not department:
            flash('El departamento es obligatorio.', 'error')
            return render_template('admin/locality_edit.html', locality=None)

        if not description:
            flash('La descripción es obligatoria.', 'error')
            return render_template('admin/locality_edit.html', locality=None)

        if Locality.query.filter_by(name=name).first():
            flash(f'Ya existe una localidad con el nombre "{name}".', 'error')
            return render_template('admin/locality_edit.html', locality=None)

        locality = Locality(
            name=name,
            department=department or None,
            description=description or None,
            is_active=bool(request.form.get('is_active')),
        )
        db.session.add(locality)
        db.session.commit()
        log_activity('LOCALITY_CREATE', f'Localidad creada: {locality.name}')
        flash(f'Localidad "{locality.name}" creada exitosamente.', 'success')
        return redirect(url_for('admin.localities'))

    return render_template('admin/locality_edit.html', locality=None)


@admin_bp.route('/localities/<int:locality_id>/edit', methods=['GET', 'POST'])
@login_required
def locality_edit(locality_id):
    locality = Locality.query.get_or_404(locality_id)

    if request.method == 'POST':
        locality.name = request.form.get('name', '').strip()
        locality.department = request.form.get('department', '').strip() or None
        locality.description = request.form.get('description', '').strip() or None
        locality.is_active = bool(request.form.get('is_active'))

        if not locality.name:
            flash('El nombre es obligatorio.', 'error')
            return render_template('admin/locality_edit.html', locality=locality)

        if not locality.department:
            flash('El departamento es obligatorio.', 'error')
            return render_template('admin/locality_edit.html', locality=locality)

        if not locality.description:
            flash('La descripción es obligatoria.', 'error')
            return render_template('admin/locality_edit.html', locality=locality)

        existing = Locality.query.filter_by(name=locality.name).first()
        if existing and existing.id != locality.id:
            flash(
                f'Ya existe una localidad con el nombre "{locality.name}".',
                'error',
            )
            return render_template('admin/locality_edit.html', locality=locality)

        db.session.commit()
        log_activity('LOCALITY_EDIT', f'Localidad editada: {locality.name}')
        flash(f'Localidad "{locality.name}" actualizada.', 'success')
        return redirect(url_for('admin.localities'))

    return render_template('admin/locality_edit.html', locality=locality)


@admin_bp.route('/localities/<int:locality_id>/delete', methods=['POST'])
@login_required
def locality_delete(locality_id):
    locality = Locality.query.get_or_404(locality_id)
    name = locality.name
    db.session.delete(locality)
    db.session.commit()
    log_activity('LOCALITY_DELETE', f'Localidad eliminada: {name}')
    flash(f'Localidad "{name}" eliminada.', 'success')
    return redirect(url_for('admin.localities'))


# --- PUNTOS DE REFERENCIA ---

@admin_bp.route('/localities/<int:locality_id>/reference-points')
@login_required
def reference_points(locality_id):
    locality = Locality.query.get_or_404(locality_id)
    points = locality.reference_points.order_by(ReferencePoint.name.asc()).all()
    return render_template('admin/reference_points.html', locality=locality, points=points)


@admin_bp.route('/localities/<int:locality_id>/reference-points/new', methods=['GET', 'POST'])
@login_required
def reference_point_new(locality_id):
    locality = Locality.query.get_or_404(locality_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'otro').strip() or 'otro'
        valid_categories = {key for key, _ in ReferencePoint.CATEGORIES}
        with_geolocation = bool(request.form.get('with_geolocation'))
        latitude = None
        longitude = None

        if category not in valid_categories:
            flash('Categoría inválida para el punto de referencia.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=None,
                                   categories=ReferencePoint.CATEGORIES)

        if with_geolocation:
            try:
                latitude = _parse_optional_coordinate(request.form.get('latitude'), -90, 90)
                longitude = _parse_optional_coordinate(request.form.get('longitude'), -180, 180)
            except ValueError:
                flash('Las coordenadas ingresadas no son válidas.', 'error')
                return render_template('admin/reference_point_edit.html',
                                       locality=locality, point=None,
                                       categories=ReferencePoint.CATEGORIES)

            if latitude is None or longitude is None:
                flash('Seleccioná un punto en el mapa o completá latitud/longitud.', 'error')
                return render_template('admin/reference_point_edit.html',
                                       locality=locality, point=None,
                                       categories=ReferencePoint.CATEGORIES)

        if not name:
            flash('El nombre es obligatorio.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=None,
                                   categories=ReferencePoint.CATEGORIES)

        phone = _opt(request.form.get('phone'))
        if not phone:
            flash('El teléfono es obligatorio.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=None,
                                   categories=ReferencePoint.CATEGORIES)

        point = ReferencePoint(
            locality_id=locality.id,
            name=name,
            category=category,
            address=_opt(request.form.get('address')),
            phone=phone,
            whatsapp=_opt(request.form.get('whatsapp')),
            email=_opt(request.form.get('email')),
            description=_opt(request.form.get('description')),
            schedule=_opt(request.form.get('schedule')),
            latitude=latitude,
            longitude=longitude,
            is_active=bool(request.form.get('is_active')),
        )
        db.session.add(point)
        db.session.commit()
        log_activity('REFERENCE_POINT_CREATE', f'Punto creado: {point.name} en {locality.name}')
        flash(f'Punto "{point.name}" creado exitosamente.', 'success')
        return redirect(url_for('admin.reference_points', locality_id=locality.id))

    return render_template('admin/reference_point_edit.html',
                           locality=locality, point=None,
                           categories=ReferencePoint.CATEGORIES)


@admin_bp.route('/localities/<int:locality_id>/reference-points/<int:point_id>/edit', methods=['GET', 'POST'])
@login_required
def reference_point_edit(locality_id, point_id):
    locality = Locality.query.get_or_404(locality_id)
    point = ReferencePoint.query.filter_by(id=point_id, locality_id=locality_id).first_or_404()

    if request.method == 'POST':
        with_geolocation = bool(request.form.get('with_geolocation'))
        category = request.form.get('category', 'otro').strip() or 'otro'
        valid_categories = {key for key, _ in ReferencePoint.CATEGORIES}
        point.name = request.form.get('name', '').strip()
        point.category = category
        point.address = _opt(request.form.get('address'))
        point.phone = _opt(request.form.get('phone'))
        point.whatsapp = _opt(request.form.get('whatsapp'))
        point.email = _opt(request.form.get('email'))
        point.description = _opt(request.form.get('description'))
        point.schedule = _opt(request.form.get('schedule'))

        if category not in valid_categories:
            flash('Categoría inválida para el punto de referencia.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=point,
                                   categories=ReferencePoint.CATEGORIES)

        if with_geolocation:
            try:
                point.latitude = _parse_optional_coordinate(request.form.get('latitude'), -90, 90)
                point.longitude = _parse_optional_coordinate(request.form.get('longitude'), -180, 180)
            except ValueError:
                flash('Las coordenadas ingresadas no son válidas.', 'error')
                return render_template('admin/reference_point_edit.html',
                                       locality=locality, point=point,
                                       categories=ReferencePoint.CATEGORIES)

            if point.latitude is None or point.longitude is None:
                flash('Seleccioná un punto en el mapa o completá latitud/longitud.', 'error')
                return render_template('admin/reference_point_edit.html',
                                       locality=locality, point=point,
                                       categories=ReferencePoint.CATEGORIES)
        else:
            point.latitude = None
            point.longitude = None

        point.is_active = bool(request.form.get('is_active'))

        if not point.name:
            flash('El nombre es obligatorio.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=point,
                                   categories=ReferencePoint.CATEGORIES)

        if not point.phone:
            flash('El teléfono es obligatorio.', 'error')
            return render_template('admin/reference_point_edit.html',
                                   locality=locality, point=point,
                                   categories=ReferencePoint.CATEGORIES)

        db.session.commit()
        log_activity('REFERENCE_POINT_EDIT', f'Punto editado: {point.name}')
        flash(f'Punto "{point.name}" actualizado.', 'success')
        return redirect(url_for('admin.reference_points', locality_id=locality.id))

    return render_template('admin/reference_point_edit.html',
                           locality=locality, point=point,
                           categories=ReferencePoint.CATEGORIES)


@admin_bp.route('/localities/<int:locality_id>/reference-points/<int:point_id>/delete', methods=['POST'])
@login_required
def reference_point_delete(locality_id, point_id):
    point = ReferencePoint.query.filter_by(id=point_id, locality_id=locality_id).first_or_404()
    name = point.name
    db.session.delete(point)
    db.session.commit()
    log_activity('REFERENCE_POINT_DELETE', f'Punto eliminado: {name}')
    flash(f'Punto "{name}" eliminado.', 'success')
    return redirect(url_for('admin.reference_points', locality_id=locality_id))