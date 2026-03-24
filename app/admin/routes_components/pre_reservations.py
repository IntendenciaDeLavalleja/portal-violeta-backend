from flask import render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required
from app.extensions import db
from app.models.camping import PreReservation, CampingService
from app.utils.logging_helper import log_activity
from app.services.reservation_service import archive_expired_pre_reservations, confirm_pre_reservation
from sqlalchemy.orm import joinedload
from .. import admin_bp
from datetime import datetime, timedelta
import io
import csv
import uuid
import random
import string


def _generate_pre_reservation_code() -> str:
    while True:
        letters = ''.join(random.choice(string.ascii_uppercase) for _ in range(3))
        numbers = ''.join(random.choice(string.digits) for _ in range(4))
        code = f'ARQ-{letters}-{numbers}'
        if not PreReservation.query.filter_by(code=code).first():
            return code

@admin_bp.route('/camping/pre-reservations', methods=['GET', 'POST'])
@login_required
def camping_pre_reservations():
    if request.method == 'POST':
        try:
            service_id = request.form.get('service_id', type=int)
            full_name = (request.form.get('full_name') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            phone = (request.form.get('phone') or '').strip()
            guests = request.form.get('guests', type=int)
            check_in_str = (request.form.get('check_in') or '').strip()
            check_out_str = (request.form.get('check_out') or '').strip()
            notes = (request.form.get('notes') or '').strip()
            lang = (request.form.get('lang') or 'es').strip().lower()
            status = (request.form.get('status') or 'pendiente').strip().lower()

            if lang not in ('es', 'en', 'pt'):
                lang = 'es'

            if status not in ('pendiente', 'confirmado'):
                status = 'pendiente'

            if not (service_id and full_name and email and phone and guests and check_in_str and check_out_str):
                flash('Completa todos los campos obligatorios para crear la pre-reserva.', 'error')
                return redirect(url_for('admin.camping_pre_reservations'))

            service = CampingService.query.filter_by(id=service_id, is_active=True).first()
            if not service:
                flash('Servicio no válido o inactivo.', 'error')
                return redirect(url_for('admin.camping_pre_reservations'))

            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

            if check_in >= check_out:
                flash('La fecha de salida debe ser posterior a la de ingreso.', 'error')
                return redirect(url_for('admin.camping_pre_reservations'))

            if guests < 1 or guests > service.capacity:
                flash(f'La cantidad de huéspedes debe estar entre 1 y {service.capacity}.', 'error')
                return redirect(url_for('admin.camping_pre_reservations'))

            if status == 'confirmado' and service.available_units <= 0:
                flash('No hay disponibilidad para crear una reserva confirmada.', 'error')
                return redirect(url_for('admin.camping_pre_reservations'))

            now = datetime.utcnow()
            reservation = PreReservation(
                code=_generate_pre_reservation_code(),
                service_id=service.id,
                full_name=full_name,
                email=email,
                phone=phone,
                guests=guests,
                check_in=check_in,
                check_out=check_out,
                notes=notes,
                lang=lang,
                status=status,
                source='admin',
                confirmation_token=str(uuid.uuid4()),
                expires_at=now + timedelta(hours=48),
                confirmed_at=now if status == 'confirmado' else None,
            )

            if status == 'confirmado':
                service.available_units = max(0, service.available_units - 1)

            db.session.add(reservation)
            db.session.commit()

            log_activity(
                'PRE_RESERVATION_CREATE_ADMIN',
                f'Pre-reserva creada manualmente ({status}) - Código: {reservation.code}'
            )
            flash(f'Pre-reserva creada correctamente ({reservation.code}).', 'success')
        except ValueError:
            flash('Formato de fechas inválido.', 'error')
        except Exception as exc:
            db.session.rollback()
            flash(f'No se pudo crear la pre-reserva: {str(exc)}', 'error')

        return redirect(url_for('admin.camping_pre_reservations'))

    archived = archive_expired_pre_reservations()
    if archived > 0:
        flash(f'Se archivaron {archived} pre-reservas vencidas automáticamente', 'info')

    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)

    query = PreReservation.query.options(joinedload(PreReservation.service))
    if status:
        query = query.filter_by(status=status)
    
    if start_date:
        query = query.filter(PreReservation.check_in >= start_date)
    if end_date:
        query = query.filter(PreReservation.check_in <= end_date)

    pagination = query.order_by(PreReservation.created_at.desc()).paginate(page=page, per_page=10)
    reservations_list = pagination.items
    
    services = CampingService.query.filter_by(is_active=True).order_by(CampingService.name_es.asc()).all()

    return render_template('admin/camping_pre_reservations.html', 
                           reservations=reservations_list, 
                           pagination=pagination,
                           status=status,
                           start_date=start_date,
                           end_date=end_date,
                           services=services)


@admin_bp.route('/camping/pre-reservations/export', methods=['GET'])
@login_required
def export_camping_pre_reservations():
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = PreReservation.query.options(joinedload(PreReservation.service))
    if status:
        query = query.filter_by(status=status)
    
    if start_date:
        query = query.filter(PreReservation.check_in >= start_date)
    if end_date:
        query = query.filter(PreReservation.check_in <= end_date)

    reservations_list = query.order_by(PreReservation.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    output.write('\ufeff')
    writer.writerow(['Código', 'Servicio', 'Origen', 'Cliente', 'Email', 'Teléfono', 'Huéspedes', 'Check-in', 'Check-out', 'Estado', 'Creado'])
    
    for res in reservations_list:
        writer.writerow([
            res.code,
            res.service.name_es if res.service else 'N/A',
            res.source,
            res.full_name,
            res.email,
            res.phone,
            res.guests,
            res.check_in.strftime('%Y-%m-%d') if res.check_in else '',
            res.check_out.strftime('%Y-%m-%d') if res.check_out else '',
            res.status,
            res.created_at.strftime('%Y-%m-%d %H:%M:%S') if res.created_at else ''
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=pre_reservas_camping.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


@admin_bp.route('/camping/pre-reservations/<int:reservation_id>/confirm', methods=['POST'])
@login_required
def confirm_camping_pre_reservation(reservation_id):
    reservation = PreReservation.query.get_or_404(reservation_id)
    ok, message = confirm_pre_reservation(reservation)
    if ok:
        flash('Pre-reserva confirmada y disponibilidad actualizada', 'success')
        log_activity('PRE_RESERVATION_CONFIRM', f'Pre-reserva confirmada {reservation.code}')
    else:
        flash(message, 'error')
    return redirect(url_for('admin.camping_pre_reservations'))


@admin_bp.route('/camping/pre-reservations/<int:reservation_id>/check-in', methods=['POST'])
@login_required
def check_in_reservation(reservation_id):
    reservation = PreReservation.query.get_or_404(reservation_id)
    if reservation.status != 'confirmado':
        flash('Solo se puede dar ingreso a reservas confirmadas', 'error')
        return redirect(url_for('admin.camping_pre_reservations'))

    reservation.status = 'activo'
    reservation.checked_in_at = datetime.utcnow()
    db.session.commit()
    log_activity('CHECK_IN', f'Ingreso registrado: {reservation.code}')
    flash('Ingreso registrado. Producto ahora "En Activo"', 'success')
    return redirect(url_for('admin.camping_pre_reservations', status='activo'))


@admin_bp.route('/camping/pre-reservations/<int:reservation_id>/archive', methods=['POST'])
@login_required
def archive_camping_pre_reservation(reservation_id):
    reservation = PreReservation.query.get_or_404(reservation_id)
    reason = (request.form.get('reason') or '').strip()
    
    if not reason:
        flash('Debes indicar un motivo para archivar la reserva', 'error')
        return redirect(url_for('admin.camping_pre_reservations'))

    if reservation.status in ['confirmado', 'activo']:
        service = reservation.service
        if service:
            service.available_units = min(service.total_units, service.available_units + 1)

    reservation.status = 'archivado_admin'
    reservation.archive_reason = reason
    reservation.archived_at = datetime.utcnow()
    db.session.commit()
    log_activity('PRE_RESERVATION_ARCHIVE', f'Reserva archivada por admin: {reservation.code} - Motivo: {reason}')
    flash('Reserva archivada con motivo', 'success')
    return redirect(url_for('admin.camping_pre_reservations'))


@admin_bp.route('/camping/pre-reservations/<int:reservation_id>/complete', methods=['POST'])
@login_required
def complete_active_reservation(reservation_id):
    reservation = PreReservation.query.get_or_404(reservation_id)
    if reservation.status != 'activo':
        flash('Solo se pueden finalizar estadías activas', 'error')
        return redirect(url_for('admin.camping_pre_reservations'))

    service = reservation.service
    if service:
        service.available_units = min(service.total_units, service.available_units + 1)
    
    reservation.status = 'completado'
    reservation.completed_at = datetime.utcnow()
    db.session.commit()
    
    log_activity('PRE_RESERVATION_COMPLETE', f'Estadía finalizada correctamente: {reservation.code}')
    flash('Estadía finalizada y cupo devuelto al inventario', 'success')
    return redirect(url_for('admin.camping_pre_reservations'))
