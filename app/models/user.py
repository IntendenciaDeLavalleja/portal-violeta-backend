from datetime import datetime, timedelta
from flask_login import UserMixin
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.extensions import db

ph = PasswordHasher()

class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_superuser = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to 2FA codes
    two_factor_codes = db.relationship('TwoFactorCode', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = ph.hash(password)

    def check_password(self, password):
        try:
            return ph.verify(self.password_hash, password)
        except (VerifyMismatchError, Exception):
            return False

    def __repr__(self):
        return f'<AdminUser {self.username}>'

class TwoFactorCode(db.Model):
    __tablename__ = 'two_factor_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, code):
        self.user_id = user_id
        self.code_hash = ph.hash(code)
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)

    def verify_code(self, code):
        if self.consumed_at or datetime.utcnow() > self.expires_at:
            return False
        try:
            return ph.verify(self.code_hash, code)
        except (VerifyMismatchError, Exception):
            return False

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True) # Null for failed logins or attempts
    username = db.Column(db.String(64), nullable=True) 
    
    action = db.Column(db.String(100), nullable=False) # Ej: LOGIN_SUCCESS, REPORT_UPDATE, CONTACT_DELETE
    details = db.Column(db.Text, nullable=True)
    
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to user
    owner = db.relationship('AdminUser', backref=db.backref('activity_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.username} at {self.timestamp}>'
