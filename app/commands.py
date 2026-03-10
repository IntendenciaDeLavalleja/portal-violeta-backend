import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import AdminUser


@click.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
@click.argument('is_superuser', default='false')
@with_appcontext
def create_admin(username, email, password, is_superuser):
    """Crea un usuario administrador del Punto Violeta Digital."""
    is_super = is_superuser.lower() == 'true'
    user = AdminUser(username=username, email=email, is_superuser=is_super)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    role = "Super Administrador" if is_super else "Administrador"
    print(f"{role} '{username}' creado exitosamente.")


@click.command('init-db')
@with_appcontext
def init_db():
    """Inicializa / actualiza las tablas de la base de datos."""
    db.create_all()
    print("Base de datos inicializada.")


# Backwards-compat stub — ya no hace nada, se mantiene para no romper Dockerfiles existentes.
@click.command('archive-expired-pre-reservations')
@with_appcontext
def archive_expired_pre_reservations_command():
    """(Stub) Este comando ya no aplica al Punto Violeta."""
    print("Este comando fue removido en la refactorización del Punto Violeta Digital.")
