from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app.auth import destino_seguro
from app.demo import USUARIOS_DEMO
from app.extensions import db
from app.models import Usuario

bp = Blueprint("auth", __name__, url_prefix="/administracion")


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
