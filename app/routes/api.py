"""Acciones que dispara el JavaScript. Reciben y devuelven JSON."""
from datetime import date

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Habitacion, Reserva
from app.services import recepcion
from app.services.recepcion import ErrorDeNegocio

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.before_request
def exigir_json():
    # Un formulario de otro sitio no puede mandar Content-Type JSON sin permiso (CORS),
    # así que exigirlo evita que otra página dispare estas acciones.
    if request.method == "POST" and not request.is_json:
        return jsonify(ok=False, error="Se esperaba JSON."), 415


@bp.errorhandler(ErrorDeNegocio)
def error_de_negocio(error):
    db.session.rollback()
    return jsonify(ok=False, error=str(error)), 409


@bp.errorhandler(404)
def no_encontrado(_error):
    return jsonify(ok=False, error="No existe."), 404


def _ok(mensaje):
    db.session.commit()
    return jsonify(ok=True, mensaje=mensaje)


@bp.post("/reservas/<int:reserva_id>/check-in")
def checkin(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)
    recepcion.hacer_checkin(reserva, date.today())
    return _ok(f"Check-in de la {reserva.habitacion.numero} hecho.")


@bp.post("/reservas/<int:reserva_id>/check-out")
def checkout(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)
    recepcion.hacer_checkout(reserva, date.today())
    return _ok(f"Check-out de la {reserva.habitacion.numero} hecho. Quedó para limpiar.")


@bp.post("/habitaciones/<int:habitacion_id>/limpieza")
def limpieza(habitacion_id):
    habitacion = db.get_or_404(Habitacion, habitacion_id)
    estado = request.json.get("estado")
    recepcion.marcar_limpieza(habitacion, estado)
    texto = "limpia" if estado == Habitacion.LIMPIA else "para limpiar"
    return _ok(f"La {habitacion.numero} quedó {texto}.")


@bp.post("/habitaciones/<int:habitacion_id>/mantenimiento")
def mantenimiento(habitacion_id):
    habitacion = db.get_or_404(Habitacion, habitacion_id)
    if request.json.get("activo"):
        nota = (request.json.get("nota") or "").strip()[:200]
        recepcion.poner_en_mantenimiento(habitacion, nota)
        return _ok(f"La {habitacion.numero} quedó bloqueada por mantenimiento.")
    recepcion.quitar_de_mantenimiento(habitacion)
    return _ok(f"La {habitacion.numero} volvió a estar habilitada.")
