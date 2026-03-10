from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.camping import Suggestion
from app.utils.logging_helper import log_activity
from .. import admin_bp

@admin_bp.route('/camping/suggestions', methods=['GET'])
@login_required
def camping_suggestions():
    status = request.args.get('status')
    query = Suggestion.query
    if status:
        query = query.filter_by(status=status)

    suggestions_list = query.order_by(Suggestion.created_at.desc()).all()
    return render_template('admin/camping_suggestions.html', suggestions=suggestions_list, status=status)


@admin_bp.route('/camping/suggestions/<int:suggestion_id>/status', methods=['POST'])
@login_required
def update_camping_suggestion_status(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    new_status = (request.form.get('status') or '').strip().lower()
    allowed = {'nuevo', 'revisado', 'archivado'}

    if new_status not in allowed:
        flash('Estado de sugerencia inválido', 'error')
        return redirect(url_for('admin.camping_suggestions'))

    suggestion.status = new_status
    db.session.commit()
    log_activity('SUGGESTION_STATUS_UPDATE', f'Sugerencia {suggestion.id} -> {new_status}')
    flash('Estado de sugerencia actualizado', 'success')
    return redirect(url_for('admin.camping_suggestions', status=request.args.get('status') or ''))
