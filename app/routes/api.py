"""Acciones que dispara el JavaScript. Reciben y devuelven JSON."""
from datetime import date

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.filtros import moneda, rango_fechas
from app.models import Habitacion, Reserva
from app.routes.auth import login_requerido
from app.services import huespedes, recepcion, reservas
from app.services.errores import ErrorDeNegocio

bp = Blueprint("api", __name__, url_prefix="/administracion/api")
bp.before_request(login_requerido)


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


@bp.get("/disponibilidad")
def disponibilidad():
    """Qué habitaciones se pueden elegir en la nueva reserva para esas fechas y personas."""
    try:
        entrada = date.fromisoformat(request.args.get("entrada", ""))
        salida = date.fromisoformat(request.args.get("salida", ""))
    except ValueError:
        return jsonify(ok=False, error="Elegí las fechas de entrada y salida."), 400
    if salida <= entrada:
        return jsonify(ok=False, error="La salida tiene que ser posterior a la entrada."), 400
    personas = request.args.get("personas", default=1, type=int)
    opciones = reservas.disponibilidad(entrada, salida, personas)
    return jsonify(ok=True, habitaciones=[
        {"id": o.habitacion.id, "estado": o.estado, "motivo": o.motivo} for o in opciones
    ])


@bp.get("/huespedes")
def buscar_huespedes():
    """Buscador de huéspedes que ya se alojaron (para no cargarlos de nuevo)."""
    return jsonify(ok=True, huespedes=[
        {
            "id": h.id,
            "nombre": h.nombre_completo,
            "documento": h.documento,
            "email": h.email,
            "telefono": h.telefono,
            "pais": huespedes.NOMBRES_PAISES.get(h.pais, h.pais),
            "estadias": len(h.reservas),
        }
        for h in huespedes.buscar(request.args.get("q", ""))
    ])


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


@bp.post("/reservas/<int:reserva_id>/no-show")
def no_show(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)
    recepcion.marcar_no_show(reserva, date.today())
    return _ok(f"{reserva.huesped.apellido} quedó como no presentado. La {reserva.habitacion.numero} se liberó.")


@bp.post("/reservas/<int:reserva_id>/mover")
def mover(reserva_id):
    """Cambio de habitación y/o fechas desde el tape chart."""
    reserva = db.get_or_404(Reserva, reserva_id)
    try:
        habitacion_id = int(request.json.get("habitacion_id"))
        entrada = date.fromisoformat(request.json.get("entrada"))
        salida = date.fromisoformat(request.json.get("salida"))
    except (TypeError, ValueError):
        raise ErrorDeNegocio("Datos inválidos.")
    habitacion = db.get_or_404(Habitacion, habitacion_id)

    total_anterior = reserva.total
    reservas.mover_reserva(reserva, habitacion, entrada, salida, date.today())
    mensaje = (
        f"{reserva.huesped.apellido}: {habitacion.numero}, del {rango_fechas(entrada, salida)} "
        f"({reserva.noches} {'noche' if reserva.noches == 1 else 'noches'})."
    )
    if reserva.total != total_anterior:
        mensaje += f" Nuevo total: {moneda(reserva.total)}."
    return _ok(mensaje)


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
        a_reubicar = recepcion.poner_en_mantenimiento(habitacion, nota, date.today())
        mensaje = f"La {habitacion.numero} quedó bloqueada por mantenimiento."
        if a_reubicar:
            cantidad = "1 reserva" if len(a_reubicar) == 1 else f"{len(a_reubicar)} reservas"
            mensaje += f" Tiene {cantidad} en los próximos días: cambialas de habitación en Reservas."
        return _ok(mensaje)
    recepcion.quitar_de_mantenimiento(habitacion)
    return _ok(f"La {habitacion.numero} volvió a estar habilitada.")
