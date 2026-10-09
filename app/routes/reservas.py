"""Tape chart: las reservas en una grilla de habitaciones × días."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from flask import Blueprint, render_template, request, url_for

from app.auth import login_requerido
from app.extensions import db
from app.models import Habitacion, Reserva

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
