from datetime import date, timedelta
from itertools import groupby

from flask import Blueprint, render_template, request

from app.auth import login_requerido
from app.extensions import db
from app.models import Habitacion, TipoHabitacion
from app.services import ocupacion

bp = Blueprint("plano", __name__, url_prefix="/administracion")
bp.before_request(login_requerido)


def _fecha_pedida():
    try:
        return date.fromisoformat(request.args.get("fecha", ""))
    except ValueError:
        return date.today()


def _contexto(fecha):
    hoy = date.today()
    estados = ocupacion.estados_del_dia(fecha, hoy)
    pisos = [(piso, list(grupo)) for piso, grupo in groupby(estados, key=lambda e: e.habitacion.piso)]
    return {
        "fecha": fecha,
        "es_hoy": fecha == hoy,
        "dia_anterior": fecha - timedelta(days=1),
        "dia_siguiente": fecha + timedelta(days=1),
        "estados": estados,
        "pisos": pisos,
        "resumen": ocupacion.resumen(estados, fecha),
        "tipos": db.session.scalars(db.select(TipoHabitacion).order_by(TipoHabitacion.tarifa_base)).all(),
        "etiquetas_estado": ocupacion.ETIQUETAS,
    }


@bp.get("/")
def index():
    return render_template("plano/index.html", **_contexto(_fecha_pedida()))


@bp.get("/plano/contenido")
def contenido():
    """Indicadores y pisos, para refrescar el plano desde JS sin recargar la página."""
    return render_template("plano/_contenido.html", **_contexto(_fecha_pedida()))


@bp.get("/plano/habitaciones/<int:habitacion_id>")
def panel(habitacion_id):
    """Panel lateral con el detalle de una habitación (fragmento HTML)."""
    habitacion = db.get_or_404(Habitacion, habitacion_id)
    fecha = _fecha_pedida()
    hoy = date.today()
    return render_template(
        "plano/_panel.html",
        d=ocupacion.detalle_habitacion(habitacion, fecha, hoy),
        fecha=fecha,
        es_hoy=fecha == hoy,
    )
