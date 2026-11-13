"""Login de la administración.

El usuario que ingresa se guarda en la sesión de Flask (session["usuario_id"]).
Todo lo que está bajo /administracion pide login; el sitio público para clientes no.
"""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, session, url_for

from app.demo import USUARIOS_DEMO
from app.extensions import db
from app.models import Usuario

bp = Blueprint("auth", __name__, url_prefix="/administracion")


# --- Controles que usan los otros blueprints (con before_request) ---------------------

def login_requerido():
    """Si no hay nadie logueado, manda al login (o responde 401 si es un pedido de la API)."""
    if g.get("usuario"):
        return None
    if request.blueprint == "api":
        return jsonify(ok=False, error="Tu sesión terminó. Volvé a ingresar."), 401
    destino = request.full_path if request.query_string else request.path
    return redirect(url_for("auth.login", next=destino))


def admin_requerido():
    """Configuración: además de estar logueado, hay que tener el rol administración."""
    if g.get("usuario") is None:
        return login_requerido()
    if g.usuario.rol != Usuario.ADMIN:
        flash("La configuración es solo para usuarios de administración.", "danger")
        return redirect(url_for("plano.index"))
    return None


def destino_seguro(destino):
    """Solo rutas internas, para que ?next= no pueda mandar a otro sitio."""
    if destino and destino.startswith("/") and not destino.startswith(("//", "/\\")):
        return destino
    return url_for("plano.index")


# --- Rutas ------------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("usuario"):
        return redirect(destino_seguro(request.args.get("next")))

    email = ""
    estado = 200
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        usuario = db.session.scalar(db.select(Usuario).where(Usuario.email == email))
        if usuario and usuario.check_password(request.form.get("password", "")):
            session.clear()
            session["usuario_id"] = usuario.id
            return redirect(destino_seguro(request.args.get("next")))
        flash("El email o la contraseña no son correctos.", "danger")
        estado = 401

    emails = set(db.session.scalars(db.select(Usuario.email)))
    return render_template(
        "auth/login.html",
        email=email,
        hay_usuarios=bool(emails),
        # Si se cargó la demo, el login muestra sus usuarios para que el profe pueda entrar
        usuarios_demo=[(e, p, rol) for _, e, p, rol in USUARIOS_DEMO if e in emails],
    ), estado


@bp.post("/logout")
def logout():
    session.clear()
    flash("Cerraste la sesión.", "success")
    return redirect(url_for("auth.login"))
