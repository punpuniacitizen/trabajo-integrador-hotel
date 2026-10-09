"""Comandos de consola (además de `demo`, que está en app/demo.py)."""
import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Usuario


@click.command("crear-usuario")
@click.option("--nombre", prompt="Nombre")
@click.option("--email", prompt="Email")
@click.option("--rol", type=click.Choice([Usuario.ADMIN, Usuario.RECEPCION]), default=Usuario.ADMIN,
              prompt="Rol", show_default=True)
@click.password_option("--password", prompt="Contraseña", confirmation_prompt="Repetir contraseña")
@with_appcontext
def crear_usuario_command(nombre, email, rol, password):
    """Crea un usuario para entrar a /administracion."""
    email = email.strip().lower()
    if db.session.scalar(db.select(Usuario).where(Usuario.email == email)):
        raise click.ClickException(f"Ya existe un usuario con el email {email}.")
    usuario = Usuario(nombre=nombre.strip(), email=email, rol=rol)
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()
    click.echo(f"Listo: {usuario.nombre} ({rol}) ya puede ingresar.")
