"""Login básico de la administración: el usuario logueado se guarda en la sesión de Flask.

Todo lo que está bajo /administracion pide login; el resto del sitio (la parte pública
para clientes) no.
"""
from flask import flash, g, jsonify, redirect, request, url_for


def login_requerido():
    """Se registra como before_request en los blueprints de administración."""
    if g.get("usuario"):
        return None
    if request.blueprint == "api":
        return jsonify(ok=False, error="Tu sesión terminó. Volvé a ingresar."), 401
    destino = request.full_path if request.query_string else request.path
    return redirect(url_for("auth.login", next=destino))


def admin_requerido():
    """before_request de Configuración: solo entra el rol administración."""
    usuario = g.get("usuario")
    if usuario is None:
        return login_requerido()
    if usuario.rol != "admin":
        flash("La configuración es solo para usuarios de administración.", "danger")
        return redirect(url_for("plano.index"))
    return None


def destino_seguro(destino):
    """Solo rutas internas, para que ?next= no pueda mandar a otro sitio."""
    if destino and destino.startswith("/") and not destino.startswith(("//", "/\\")):
        return destino
    return url_for("plano.index")
