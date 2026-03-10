from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.agenda import Procedure
from app.utils.logging_helper import log_activity
from .. import admin_bp

@admin_bp.route('/procedures', methods=['GET', 'POST'])
@login_required
def procedures():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        cost = request.form.get('cost')
        description = request.form.get('description')
        requirements_raw = request.form.get('requirements') or ''
        
        if not name or not category:
            flash('El nombre y la categoría son requeridos', 'error')
        else:
            req_list = [r.strip() for r in requirements_raw.split('\n') if r.strip()]
            procedure = Procedure(name=name, category=category, cost=cost, description=description)
            procedure.requirements = req_list
            db.session.add(procedure)
            db.session.commit()
            log_activity("PROCEDURE_CREATE", f"Trámite creado: {name}")
            flash(f'Trámite {name} creado correctamente', 'success')
        return redirect(url_for('admin.procedures'))
        
    all_procedures = Procedure.query.order_by(Procedure.name).all()
    return render_template('admin/procedures.html', procedures=all_procedures)

@admin_bp.route('/procedures/<int:id>/delete', methods=['POST'])
@login_required
def delete_procedure(id):
    procedure = Procedure.query.get_or_404(id)
    name = procedure.name
    
    if procedure.slots.count() > 0 or procedure.reservations.count() > 0:
        flash('No se puede eliminar un trámite que tiene reservas asociadas', 'error')
    else:
        db.session.delete(procedure)
        db.session.commit()
        log_activity("PROCEDURE_DELETE", f"Trámite eliminado: {name}")
        flash(f'Trámite {name} eliminado', 'success')
        
    return redirect(url_for('admin.procedures'))

@admin_bp.route('/procedures/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_procedure(id):
    procedure = Procedure.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        cost = request.form.get('cost')
        description = request.form.get('description')
        requirements_raw = request.form.get('requirements') or ''

        if not name or not category:
            flash('El nombre y la categoría son requeridos', 'error')
            return redirect(url_for('admin.edit_procedure', id=procedure.id))

        procedure.name = name
        procedure.category = category
        procedure.cost = cost
        procedure.description = description
        procedure.requirements = [r.strip() for r in requirements_raw.split('\n') if r.strip()]

        db.session.commit()
        log_activity("PROCEDURE_UPDATE", f"Trámite actualizado: {procedure.name}")
        flash('Trámite actualizado correctamente', 'success')
        return redirect(url_for('admin.procedures'))

    return render_template('admin/procedure_edit.html', procedure=procedure)
