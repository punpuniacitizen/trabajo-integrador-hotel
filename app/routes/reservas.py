"""Tape chart (las reservas en una grilla de habitaciones × días) y alta de reservas."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_requerido
from app.extensions import db
from app.filtros import rango_fechas
from app.models import Habitacion, Huesped, Reserva, TipoHabitacion
from app.services import huespedes
from app.services import reservas as servicio
from app.services.errores import ErrorDeNegocio

bp = Blueprint("reservas", __name__, url_prefix="/administracion/reservas")
bp.before_request(login_requerido)

# Por defecto la grilla arranca unos días antes de hoy, para ver lo que acaba de pasar
DIAS_ANTES_DE_HOY = 3
SALTO_DIAS = 7


@dataclass
class Barra:
    """Una reserva (o un bloqueo por mantenimiento) dibujada en la grilla.

    Cada día ocupa dos medias columnas: la estadía arranca en la segunda mitad del día de
    entrada (check-in a la tarde) y termina en la primera mitad del día de salida (check-out
    a la mañana). Así, el que sale y el que entra el mismo día quedan pegados sin pisarse.
    La columna 1 es la de la habitación.
    """

    columna_desde: int
    columna_hasta: int
    corta_izquierda: bool
    corta_derecha: bool
    reserva: Reserva | None = None
    detalle_url: str | None = None


def _columnas(entrada, salida, desde, dias):
    inicio = 3 + 2 * (entrada - desde).days
    fin = 3 + 2 * (salida - desde).days
    ultima = 2 + 2 * dias
    return max(inicio, 2), min(fin, ultima), inicio < 2, fin > ultima


def _parametros():
    hoy = date.today()
    try:
        desde = date.fromisoformat(request.args.get("desde", ""))
    except ValueError:
        desde = hoy - timedelta(days=DIAS_ANTES_DE_HOY)
    dias = 30 if request.args.get("dias") == "30" else 14
    return desde, dias, hoy


def _fecha_para_el_plano(reserva, hoy):
    """El día que muestra la reserva en el panel del plano (hoy, si está dentro de la estadía)."""
    ultima_noche = reserva.salida - timedelta(days=1)
    return min(max(hoy, reserva.entrada), ultima_noche)


def _contexto(desde, dias, hoy):
    hasta = desde + timedelta(days=dias)
    habitaciones = db.session.scalars(
        db.select(Habitacion).order_by(Habitacion.piso, Habitacion.numero)
    ).all()
    reservas = db.session.scalars(
        db.select(Reserva)
        .where(Reserva.estado.notin_(Reserva.INACTIVAS), Reserva.entrada < hasta, Reserva.salida > desde)
        .order_by(Reserva.entrada)
    ).all()

    barras = defaultdict(list)
    noches_ocupadas = 0
    for reserva in reservas:
        columnas = _columnas(reserva.entrada, reserva.salida, desde, dias)
        fecha_plano = _fecha_para_el_plano(reserva, hoy)
        url = url_for("plano.index", fecha=fecha_plano.isoformat()) + f"#hab-{reserva.habitacion.numero}"
        barras[reserva.habitacion_id].append(Barra(*columnas, reserva=reserva, detalle_url=url))
        noches_ocupadas += (min(reserva.salida, hasta) - max(reserva.entrada, desde)).days

    # Las habitaciones en mantenimiento muestran un bloqueo desde hoy (no tiene fecha de fin)
    if hoy < hasta:
        inicio_bloqueo = max(hoy, desde)
        for habitacion in habitaciones:
            if habitacion.fuera_de_servicio:
                desde_col = 2 + 2 * (inicio_bloqueo - desde).days
                barras[habitacion.id].append(Barra(desde_col, 2 + 2 * dias, False, True))

    habilitadas = sum(1 for h in habitaciones if not h.fuera_de_servicio)
    return {
        "desde": desde,
        "hasta": hasta,
        "ultimo_dia": hasta - timedelta(days=1),
        "dias": dias,
        "hoy": hoy,
        "fechas": [desde + timedelta(days=i) for i in range(dias)],
        "pisos": [(piso, list(grupo)) for piso, grupo in groupby(habitaciones, key=lambda h: h.piso)],
        "barras": barras,
        "ocupacion": round(100 * noches_ocupadas / (habilitadas * dias)) if habilitadas else 0,
        "anterior": desde - timedelta(days=SALTO_DIAS),
        "siguiente": desde + timedelta(days=SALTO_DIAS),
    }


@bp.get("/")
def index():
    return render_template("reservas/index.html", **_contexto(*_parametros()))


@bp.get("/grilla")
def grilla():
    """Solo la grilla, para refrescarla desde JS después de mover una reserva."""
    return render_template("reservas/_tape.html", **_contexto(*_parametros()))


# --- Nueva reserva ------------------------------------------------------------------------

def _fecha(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None


def _entero(texto):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return None


def _url_volver(volver, fecha=None):
    """A dónde vuelve el formulario: al plano o al tape chart, según desde dónde se abrió."""
    if volver == "plano":
        return url_for("plano.index", fecha=fecha.isoformat()) if fecha else url_for("plano.index")
    return url_for("reservas.index")


def _destino(reserva, volver, hoy):
    """Después de crearla se muestra la reserva: en el plano (con su panel abierto) o en el tape chart."""
    if volver == "plano":
        return _url_volver("plano", reserva.entrada) + f"#hab-{reserva.habitacion.numero}"
    # Si se ve bien en la grilla que el tape chart muestra por defecto, no hace falta moverla
    if reserva.entrada <= hoy + timedelta(days=SALTO_DIAS):
        url = url_for("reservas.index")
    else:
        url = url_for("reservas.index", desde=(reserva.entrada - timedelta(days=DIAS_ANTES_DE_HOY)).isoformat())
    return url + f"#reserva-{reserva.id}"


def _formulario(datos, hoy, error=None):
    """Contexto del formulario. datos: lo que vino en la URL (para precompletar desde el plano o
    el tape chart) o lo que se mandó (si hubo un error, para no perderlo)."""
    entrada = _fecha(datos.get("entrada"))
    if entrada is None or entrada < hoy:
        entrada = hoy
    salida = _fecha(datos.get("salida"))
    if salida is None or salida <= entrada:
        salida = entrada + timedelta(days=1)

    habitacion_id = _entero(datos.get("habitacion_id") or datos.get("habitacion"))
    habitacion = db.session.get(Habitacion, habitacion_id) if habitacion_id else None
    max_personas = db.session.scalar(db.select(db.func.max(TipoHabitacion.capacidad))) or 1
    personas = _entero(datos.get("personas"))
    if personas is None:
        # Si se eligió una habitación de antemano (una simple, por ejemplo), que entren
        personas = min(2, habitacion.tipo.capacidad) if habitacion else 2
    personas = min(max(personas, 1), max_personas)

    opciones = servicio.disponibilidad(entrada, salida, personas)
    elegida = next((o for o in opciones if o.habitacion.id == habitacion_id and o.libre), None)
    huesped_id = _entero(datos.get("huesped_id"))

    return {
        "datos": datos,
        "entrada": entrada,
        "salida": salida,
        "salida_minima": entrada + timedelta(days=1),
        "noches": (salida - entrada).days,
        "personas": personas,
        "max_personas": max_personas,
        "grupos": [(tipo, list(grupo)) for tipo, grupo in groupby(opciones, key=lambda o: o.habitacion.tipo)],
        "libres": sum(o.libre for o in opciones),
        "total_habitaciones": len(opciones),
        "elegida": elegida,
        "huesped": db.session.get(Huesped, huesped_id) if huesped_id else None,
        "paises": huespedes.PAISES,
        "volver": datos.get("volver") or "tape",
        "url_cancelar": _url_volver(datos.get("volver"), entrada),
        "maximo_noches": servicio.MAXIMO_NOCHES,
        "error": error,
    }


def _crear(datos, hoy):
    entrada, salida = _fecha(datos.get("entrada")), _fecha(datos.get("salida"))
    if entrada is None or salida is None:
        raise ErrorDeNegocio("Elegí las fechas de entrada y salida.")
    habitacion_id = _entero(datos.get("habitacion_id"))
    habitacion = db.session.get(Habitacion, habitacion_id) if habitacion_id else None
    if habitacion is None:
        raise ErrorDeNegocio("Elegí una habitación.")
    personas = _entero(datos.get("personas")) or 0

    texto_pagado = (datos.get("pagado") or "").strip()
    pagado = _entero(texto_pagado) if texto_pagado else 0
    if pagado is None:
        raise ErrorDeNegocio("Lo pagado tiene que ser un número entero, sin puntos ni comas.")

    huesped_id = _entero(datos.get("huesped_id"))
    if huesped_id:
        huesped = db.session.get(Huesped, huesped_id)
        if huesped is None:
            raise ErrorDeNegocio("El huésped elegido ya no existe. Buscalo de nuevo.")
    else:
        huesped = huespedes.nuevo_huesped(
            datos.get("nombre"), datos.get("apellido"), datos.get("documento"),
            datos.get("email"), datos.get("telefono"), datos.get("pais"),
        )

    return servicio.crear_reserva(
        habitacion, huesped, entrada, salida, personas, hoy,
        pagado=pagado, notas=datos.get("notas"), checkin=datos.get("checkin") == "1",
    )


@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    hoy = date.today()
    if request.method == "GET":
        return render_template("reservas/nueva.html", **_formulario(request.args, hoy))

    datos = request.form
    try:
        reserva = _crear(datos, hoy)
    except ErrorDeNegocio as error:
        db.session.rollback()
        return render_template("reservas/nueva.html", **_formulario(datos, hoy, error=str(error))), 422
    db.session.commit()

    mensaje = (f"Reserva {reserva.codigo} creada: {reserva.huesped.nombre_completo} en la "
               f"{reserva.habitacion.numero}, {rango_fechas(reserva.entrada, reserva.salida)}.")
    if reserva.estado == Reserva.EN_CURSO:
        mensaje += " Check-in hecho."
    flash(mensaje, "success")
    return redirect(_destino(reserva, datos.get("volver"), hoy))
