from flask import render_template, request, Response, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import ActivityLog
from .. import admin_bp
from datetime import datetime, timedelta

@admin_bp.route('/audit-logs')
@login_required
def audit_logs():
    if not current_user.is_superuser:
        abort(403)

    action_filter = request.args.get('action') or None
    username_filter = request.args.get('username') or None
    date_filter = request.args.get('date') or None

    query = ActivityLog.query
    if action_filter:
        query = query.filter(ActivityLog.action == action_filter)
    if username_filter:
        query = query.filter(ActivityLog.username == username_filter)
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            start_dt = datetime.combine(date_obj, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            query = query.filter(ActivityLog.timestamp >= start_dt, ActivityLog.timestamp < end_dt)
        except ValueError:
            date_filter = None

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(ActivityLog.timestamp.desc()).paginate(page=page, per_page=50)

    actions = [row[0] for row in db.session.query(ActivityLog.action).distinct().order_by(ActivityLog.action.asc()).all()]
    users = [row[0] for row in db.session.query(ActivityLog.username).filter(ActivityLog.username.isnot(None)).distinct().order_by(ActivityLog.username.asc()).all()]

    return render_template('admin/audit_logs.html',
                           logs=pagination.items,
                           pagination=pagination,
                           actions=actions,
                           users=users,
                           current_action=action_filter,
                           current_username=username_filter,
                           current_date=date_filter)

@admin_bp.route('/audit-logs/export')
@login_required
def export_audit_logs():
    if not current_user.is_superuser:
        abort(403)

    action_filter = request.args.get('action') or None
    username_filter = request.args.get('username') or None
    date_filter = request.args.get('date') or None

    query = ActivityLog.query
    if action_filter:
        query = query.filter(ActivityLog.action == action_filter)
    if username_filter:
        query = query.filter(ActivityLog.username == username_filter)
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            start_dt = datetime.combine(date_obj, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            query = query.filter(ActivityLog.timestamp >= start_dt, ActivityLog.timestamp < end_dt)
        except ValueError:
            pass

    logs = query.order_by(ActivityLog.timestamp.desc()).all()

    def generate_csv():
        header = 'id,timestamp,username,action,ip_address,user_agent,details\n'
        yield header
        for log in logs:
            row = [
                str(log.id),
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
                (log.username or '').replace('"', '""'),
                (log.action or '').replace('"', '""'),
                (log.ip_address or '').replace('"', '""'),
                (log.user_agent or '').replace('"', '""'),
                (log.details or '').replace('"', '""')
            ]
            yield '"' + '","'.join(row) + '"\n'

    filename = 'audit_logs.csv'
    return Response(
        generate_csv(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
