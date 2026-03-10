from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.agenda import Locality, Procedure, AppointmentSlot
from app.utils.logging_helper import log_activity
from .. import admin_bp
from datetime import datetime

@admin_bp.route('/slots', methods=['GET', 'POST'])
@login_required
def slots():
    if request.method == 'POST':
        locality_id = request.form.get('locality_id')
        procedure_id = request.form.get('procedure_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        capacity = int(request.form.get('capacity', 1))
        
        try:
            if not (locality_id and procedure_id and date_str and time_str):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('admin.slots'))

            locality_id = int(locality_id)
            procedure_id = int(procedure_id)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            
            # Simple check for duplicates
            existing = AppointmentSlot.query.filter_by(
                locality_id=locality_id,
                procedure_id=procedure_id,
                date=date_obj,
                time=time_obj
            ).first()
            
            if existing:
                flash('Ya existe un turno en ese horario para esta localidad', 'warning')
            else:
                slot = AppointmentSlot(
                    locality_id=locality_id,
                    procedure_id=procedure_id,
                    date=date_obj,
                    time=time_obj,
                    max_capacity=capacity
                )
                db.session.add(slot)
                db.session.commit()
                flash('Turno creado correctamente', 'success')
        except Exception as e:
            flash(f'Error al crear turno: {str(e)}', 'error')
            
        return redirect(url_for('admin.slots'))
        
    page = request.args.get('page', 1, type=int)
    locality_filter = request.args.get('locality_id')
    date_filter = request.args.get('date')
    
    query = AppointmentSlot.query
    if locality_filter:
        query = query.filter_by(locality_id=locality_filter)
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=date_obj)
        except ValueError:
            pass
        
    pagination = query.order_by(AppointmentSlot.date.desc(), AppointmentSlot.time.asc()).paginate(page=page, per_page=50)
    
    localities_list = Locality.query.order_by(Locality.name).all()
    procedures_list = Procedure.query.order_by(Procedure.name).all()
    return render_template('admin/slots.html', 
                           slots=pagination.items, 
                           pagination=pagination, 
                           localities=localities_list,
                           procedures=procedures_list)

@admin_bp.route('/slots/<int:id>/delete', methods=['POST'])
@login_required
def delete_slot(id):
    slot = AppointmentSlot.query.get_or_404(id)
    if slot.current_bookings > 0:
        flash('No se puede eliminar un turno que ya tiene reservas', 'error')
    else:
        db.session.delete(slot)
        db.session.commit()
        flash('Turno eliminado', 'success')
    return redirect(url_for('admin.slots'))

@admin_bp.route('/slots/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_slot(id):
    slot = AppointmentSlot.query.get_or_404(id)

    if request.method == 'POST':
        locality_id = request.form.get('locality_id')
        procedure_id = request.form.get('procedure_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        capacity = request.form.get('capacity')

        if not (locality_id and procedure_id and date_str and time_str and capacity):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.edit_slot', id=slot.id))

        try:
            locality_id = int(locality_id)
            procedure_id = int(procedure_id)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            capacity = int(capacity)

            duplicate = AppointmentSlot.query.filter(
                AppointmentSlot.id != slot.id,
                AppointmentSlot.locality_id == locality_id,
                AppointmentSlot.procedure_id == procedure_id,
                AppointmentSlot.date == date_obj,
                AppointmentSlot.time == time_obj
            ).first()

            if duplicate:
                flash('Ya existe un turno con esos datos', 'warning')
                return redirect(url_for('admin.edit_slot', id=slot.id))

            slot.locality_id = locality_id
            slot.procedure_id = procedure_id
            slot.date = date_obj
            slot.time = time_obj
            slot.max_capacity = capacity

            if slot.current_bookings > slot.max_capacity:
                slot.current_bookings = slot.max_capacity

            db.session.commit()
            log_activity("SLOT_UPDATE", f"Turno actualizado ID: {slot.id}")
            flash('Turno actualizado correctamente', 'success')
            return redirect(url_for('admin.slots'))
        except ValueError:
            flash('Datos inválidos para la actualización', 'error')
            return redirect(url_for('admin.edit_slot', id=slot.id))

    localities_list = Locality.query.order_by(Locality.name).all()
    procedures_list = Procedure.query.order_by(Procedure.name).all()
    return render_template('admin/slot_edit.html', slot=slot, localities=localities_list, procedures=procedures_list)
