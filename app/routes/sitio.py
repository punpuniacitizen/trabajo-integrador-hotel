"""Sitio público del hotel: habitaciones y reserva online (sin login).

La reserva es un demostrador: el cliente elige tipo de habitación, fechas, personas y
pone su nombre. No hay pago. La reserva aparece al instante en el plano y el tape chart.
"""
from datetime import date, timedelta

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Reserva, TipoHabitacion
from app.services import reservas
from app.services.errores import ErrorDeNegocio

bp = Blueprint("sitio", __name__)


def _tipos():
    """Los tipos que se ofrecen en el sitio: los que tienen al menos una habitación."""
    return db.session.scalars(
        db.select(TipoHabitacion).where(TipoHabitacion.habitaciones.any()).order_by(TipoHabitacion.tarifa_base)
    ).all()


def _fecha(texto, por_defecto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return por_defecto


def _entero(texto, por_defecto):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return por_defecto


@bp.get("/")
def inicio():
    return render_template("sitio/inicio.html", tipos=_tipos())


@bp.get("/habitaciones/<slug>")
def habitacion(slug):
    tipo = db.session.scalar(db.select(TipoHabitacion).where(TipoHabitacion.slug == slug))
    if tipo is None:
        abort(404)
    return render_template("sitio/habitacion.html", tipo=tipo, tipos=_tipos())


@bp.route("/reservar", methods=["GET", "POST"])
def reservar():
    tipos = _tipos()
    if not tipos:
        abort(404)
    hoy = date.today()
    datos = request.form if request.method == "POST" else request.args

    slug = datos.get("tipo")
    tipo = next((t for t in tipos if t.slug == slug), None) or next((t for t in tipos if t.capacidad >= 2), tipos[0])
    entrada = _fecha(datos.get("entrada"), hoy + timedelta(days=1))
    salida = _fecha(datos.get("salida"), entrada + timedelta(days=2))
    personas = _entero(datos.get("personas"), min(2, tipo.capacidad))
    nombre = datos.get("nombre", "")
    email = datos.get("email", "")

    error = None
    if request.method == "POST":
        try:
            reserva = reservas.crear_reserva_web(tipo, entrada, salida, personas, nombre, email, hoy)
            db.session.commit()
            return redirect(url_for("sitio.confirmacion", token=reserva.token))
        except ErrorDeNegocio as e:
            db.session.rollback()
            error = str(e)

    return render_template(
        "sitio/reservar.html",
        tipos=tipos,
        tipo=tipo,
        entrada=entrada,
        salida=salida,
        personas=personas,
        nombre=nombre,
        email=email,
        error=error,
        hoy=hoy,
    ), 422 if error else 200


@bp.get("/reserva/<token>")
def confirmacion(token):
    reserva = db.session.scalar(db.select(Reserva).where(Reserva.token == token))
    if reserva is None:
        abort(404)
    return render_template("sitio/confirmacion.html", reserva=reserva, tipo=reserva.habitacion.tipo)
