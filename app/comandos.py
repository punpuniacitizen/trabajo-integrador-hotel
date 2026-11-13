"""Comandos de consola (además de `demo`, que está en app/demo.py)."""
import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Usuario
from app.services.configuracion import crear_usuario
from app.services.errores import ErrorDeNegocio


@click.command("crear-usuario")
@click.option("--nombre", prompt="Nombre")
@click.option("--email", prompt="Email")
@click.option("--rol", type=click.Choice([Usuario.ADMIN, Usuario.RECEPCION]), default=Usuario.ADMIN,
              prompt="Rol", show_default=True)
@click.password_option("--password", prompt="Contraseña", confirmation_prompt="Repetir contraseña")
@with_appcontext
def crear_usuario_command(nombre, email, rol, password):
    """Crea un usuario para entrar a /administracion (el primero, si no se cargó la demo)."""
    try:
        usuario = crear_usuario(nombre, email, rol, password)
    except ErrorDeNegocio as error:
        raise click.ClickException(str(error)) from None
    db.session.commit()
    click.echo(f"Listo: {usuario.nombre} ({rol}) ya puede ingresar.")
