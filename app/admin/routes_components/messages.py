"""
Gestión de mensajes del formulario de contacto del Punto Violeta Digital.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.violeta import ContactMessage
from app.utils.logging_helper import log_activity
from .. import admin_bp


@admin_bp.route('/messages')
@login_required
def messages():
    status_filter = request.args.get('status', '')
    query = ContactMessage.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    messages_list = query.order_by(ContactMessage.created_at.desc()).all()
    counts = {
        'nuevo': ContactMessage.query.filter_by(status='nuevo').count(),
        'leido': ContactMessage.query.filter_by(status='leído').count(),
        'respondido': ContactMessage.query.filter_by(status='respondido').count(),
        'archivado': ContactMessage.query.filter_by(status='archivado').count(),
        'total': ContactMessage.query.count(),
    }
    return render_template('admin/messages.html',
                           messages=messages_list,
                           status_filter=status_filter,
                           counts=counts)


@admin_bp.route('/messages/<int:message_id>')
@login_required
def message_detail(message_id):
    msg = ContactMessage.query.get_or_404(message_id)
    # Auto-marcar como leído al abrir
    if msg.status == ContactMessage.STATUS_NEW:
        msg.status = ContactMessage.STATUS_READ
        db.session.commit()
    return render_template('admin/message_detail.html', msg=msg)


@admin_bp.route('/messages/<int:message_id>/status', methods=['POST'])
@login_required
def message_update_status(message_id):
    msg = ContactMessage.query.get_or_404(message_id)
    new_status = request.form.get('status', '').strip()
    valid_statuses = [
        ContactMessage.STATUS_NEW,
        ContactMessage.STATUS_READ,
        ContactMessage.STATUS_REPLIED,
        ContactMessage.STATUS_ARCHIVED,
    ]
    if new_status not in valid_statuses:
        flash('Estado inválido.', 'error')
        return redirect(url_for('admin.message_detail', message_id=message_id))

    notes = request.form.get('notes', '').strip()
    msg.status = new_status
    if notes:
        msg.notes = notes
    db.session.commit()
    log_activity('MESSAGE_STATUS_UPDATE', f'Mensaje #{message_id} marcado como "{new_status}"')
    flash(f'Mensaje actualizado como "{new_status}".', 'success')
    return redirect(url_for('admin.messages'))


@admin_bp.route('/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def message_delete(message_id):
    msg = ContactMessage.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()
    log_activity('MESSAGE_DELETE', f'Mensaje #{message_id} eliminado')
    flash('Mensaje eliminado.', 'success')
    return redirect(url_for('admin.messages'))
