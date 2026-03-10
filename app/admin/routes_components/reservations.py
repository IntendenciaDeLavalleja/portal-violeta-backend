from flask import render_template, request, redirect, url_for, flash, Response
from flask_login import login_required
from app.extensions import db
from app.models.agenda import AppointmentSlot, Reservation
from app.utils.logging_helper import log_activity
from sqlalchemy.orm import joinedload
from .. import admin_bp
from datetime import date
import random
import string
import uuid


def _generate_reservation_code() -> str:
    while True:
        code = f"RSV-{''.join(random.choice(string.digits) for _ in range(6))}"
        if not Reservation.query.filter_by(code=code).first():
            return code


@admin_bp.route('/reservations', methods=['GET', 'POST'])
@login_required
def reservations():
    if request.method == 'POST':
        try:
            slot_id = request.form.get('slot_id', type=int)
            ci = (request.form.get('ci') or '').strip()
            first_name = (request.form.get('first_name') or '').strip()
            last_name = (request.form.get('last_name') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            status = (request.form.get('status') or 'pending').strip().lower()

            if status not in ('pending', 'confirmed'):
                status = 'pending'

            if not (slot_id and ci and first_name and last_name and email):
                flash('Completa todos los campos obligatorios para crear la reserva.', 'error')
                return redirect(url_for('admin.reservations'))

            slot = AppointmentSlot.query.get(slot_id)
            if not slot or not slot.is_active:
                flash('Turno no válido o inactivo.', 'error')
                return redirect(url_for('admin.reservations'))

            if slot.date < date.today():
                flash('No se pueden crear reservas en turnos pasados.', 'error')
                return redirect(url_for('admin.reservations'))

            if slot.current_bookings >= slot.max_capacity:
                flash('El turno seleccionado ya no tiene cupos disponibles.', 'error')
                return redirect(url_for('admin.reservations'))

            reservation = Reservation(
                code=_generate_reservation_code(),
                ci=ci,
                first_name=first_name,
                last_name=last_name,
                email=email,
                procedure_id=slot.procedure_id,
                locality_id=slot.locality_id,
                slot_id=slot.id,
                date=slot.date,
                time=slot.time,
                status=status,
                source='admin',
                confirmation_token=str(uuid.uuid4()),
                cancellation_token=str(uuid.uuid4()),
            )

            slot.current_bookings += 1
            db.session.add(reservation)
            db.session.commit()

            log_activity('RESERVATION_CREATE_ADMIN', f'Reserva creada manualmente: {reservation.code}')
            flash(f'Reserva creada correctamente ({reservation.code}).', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'No se pudo crear la reserva: {str(exc)}', 'error')

        return redirect(url_for('admin.reservations'))

    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'active')
    search = request.args.get('search', '').strip()

    query = Reservation.query.options(
        joinedload(Reservation.procedure),
        joinedload(Reservation.locality)
    ).join(AppointmentSlot)

    if status_filter == 'active':
        query = query.filter(Reservation.status.in_(['pending', 'confirmed']))
    elif status_filter == 'attended':
        query = query.filter(Reservation.status == 'attended')
    elif status_filter == 'no_show':
        query = query.filter(Reservation.status == 'expired')
    elif status_filter == 'cancelled':
        query = query.filter(Reservation.status == 'cancelled')

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            (Reservation.code.ilike(search_like)) |
            (Reservation.email.ilike(search_like)) |
            (Reservation.ci.ilike(search_like))
        )
    
    pagination = query.order_by(AppointmentSlot.date.desc(), AppointmentSlot.time.desc()).paginate(page=page, per_page=30)

    available_slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.procedure),
        joinedload(AppointmentSlot.locality),
    ).filter(
        AppointmentSlot.is_active.is_(True),
        AppointmentSlot.date >= date.today(),
        AppointmentSlot.current_bookings < AppointmentSlot.max_capacity,
    ).order_by(AppointmentSlot.date.asc(), AppointmentSlot.time.asc()).all()
    
    return render_template('admin/reservations.html', 
                           reservations=pagination.items, 
                           pagination=pagination,
                           status_filter=status_filter,
                           search=search,
                           available_slots=available_slots)

@admin_bp.route('/reservations/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(id):
    res = Reservation.query.get_or_404(id)
    slot = res.slot
    
    # Update capacity
    slot.current_bookings = max(0, slot.current_bookings - 1)
    res.status = 'cancelled'
    db.session.commit()
    
    log_activity("RESERVATION_CANCEL_ADMIN", f"Reserva {res.code} cancelada por admin")
    flash(f'Reserva {res.code} cancelada', 'success')
    return redirect(url_for('admin.reservations', status=request.args.get('status', 'active')))

@admin_bp.route('/reservations/<int:id>/attended', methods=['POST'])
@login_required
def mark_reservation_attended(id):
    res = Reservation.query.get_or_404(id)
    if res.status in ['pending', 'confirmed']:
        res.status = 'attended'
        db.session.commit()
        log_activity("RESERVATION_ATTENDED", f"Reserva {res.code} efectivizada")
        flash(f'Reserva {res.code} efectivizada', 'success')
    return redirect(url_for('admin.reservations', status=request.args.get('status', 'active')))

@admin_bp.route('/reservations/<int:id>/no-show', methods=['POST'])
@login_required
def mark_reservation_no_show(id):
    res = Reservation.query.get_or_404(id)
    if res.status in ['pending', 'confirmed']:
        res.status = 'expired'
        db.session.commit()
        log_activity("RESERVATION_NO_SHOW", f"Reserva {res.code} no efectivizada")
        flash(f'Reserva {res.code} marcada como no efectivizada', 'warning')
    return redirect(url_for('admin.reservations', status=request.args.get('status', 'active')))

@admin_bp.route('/reservations/export')
@login_required
def export_reservations():
    status_filter = request.args.get('status', 'active')
    search = request.args.get('search', '').strip()

    query = Reservation.query.join(AppointmentSlot)
    if status_filter == 'active':
        query = query.filter(Reservation.status.in_(['pending', 'confirmed']))
    elif status_filter == 'attended':
        query = query.filter(Reservation.status == 'attended')
    elif status_filter == 'no_show':
        query = query.filter(Reservation.status == 'expired')
    elif status_filter == 'cancelled':
        query = query.filter(Reservation.status == 'cancelled')

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            (Reservation.code.ilike(search_like)) |
            (Reservation.email.ilike(search_like)) |
            (Reservation.ci.ilike(search_like))
        )

    reservations_list = query.order_by(AppointmentSlot.date.desc(), AppointmentSlot.time.desc()).all()

    lines = []
    header = 'codigo,ci,nombre,apellido,email,tramite,localidad,fecha,hora,estado,origen,creado\n'
    lines.append(header)
    for res in reservations_list:
        row = [
            (res.code or '').replace('"', '""'),
            (res.ci or '').replace('"', '""'),
            (res.first_name or '').replace('"', '""'),
            (res.last_name or '').replace('"', '""'),
            (res.email or '').replace('"', '""'),
            (res.procedure.name if res.procedure else '').replace('"', '""'),
            (res.locality.name if res.locality else '').replace('"', '""'),
            res.date.strftime('%Y-%m-%d') if res.date else '',
            res.time.strftime('%H:%M') if res.time else '',
            (res.status or '').replace('"', '""'),
            (res.source or 'web').replace('"', '""'),
            res.created_at.strftime('%Y-%m-%d %H:%M:%S') if res.created_at else ''
        ]
        lines.append('"' + '","'.join(row) + '"\n')

    filename = 'reservas_filtradas.csv'
    return Response(
        ''.join(lines),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
