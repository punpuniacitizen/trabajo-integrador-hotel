"""Estado de las habitaciones en una fecha.

La ocupación no se guarda en la base: se calcula a partir de las reservas.
La habitación solo guarda su estado físico (limpieza y mantenimiento).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.extensions import db
from app.models import Habitacion, Reserva

LIBRE = "libre"
OCUPADA = "ocupada"
LLEGA = "llega"
SALE = "sale"
SUCIA = "sucia"
MANTENIMIENTO = "mantenimiento"

ETIQUETAS = {
    LIBRE: "Libre",
    OCUPADA: "Ocupada",
    LLEGA: "Llega",
    SALE: "Sale",
    SUCIA: "Sucia",
    MANTENIMIENTO: "Mantenimiento",
}


@dataclass
class EstadoHabitacion:
    habitacion: Habitacion
    estado: str
    fecha: date
    es_hoy: bool = False
    reserva: Reserva | None = None  # la reserva que explica el estado
    duerme: Reserva | None = None  # la reserva que ocupa la noche de esa fecha
    llega_despues: Reserva | None = None  # ese día sale un huésped y entra otro
    sucia: bool = False

    @property
    def atrasada(self):
        """Tenía que llegar un día anterior y todavía no hizo el check-in."""
        return self.estado == LLEGA and self.duerme.entrada < self.fecha

    @property
    def etiqueta(self):
        if self.atrasada:
            return "Atrasada"
        texto = ETIQUETAS[self.estado]
        if self.es_hoy and self.estado in (LLEGA, SALE):
            return f"{texto} hoy"
        return texto


@dataclass
class DetalleHabitacion:
    estado: EstadoHabitacion
    proxima: Reserva | None
    puede_checkin: bool
    puede_checkout: bool  # el no-show se ofrece en el mismo caso que el check-in


def _consulta_reservas(fecha, hoy):
    """Reservas no canceladas que tocan la fecha (incluye las que salen ese día)."""
    toca_la_fecha = db.and_(Reserva.entrada <= fecha, Reserva.salida >= fecha)
    if fecha == hoy:
        # Un huésped que debía irse antes y todavía no hizo el check-out sigue en la habitación.
        toca_la_fecha = db.or_(toca_la_fecha, db.and_(Reserva.salida < fecha, Reserva.estado == Reserva.EN_CURSO))
    return db.select(Reserva).where(Reserva.estado.notin_(Reserva.INACTIVAS), toca_la_fecha)


def calcular_estado(habitacion, reservas, fecha, hoy):
    """reservas: las de esta habitación que devuelve _consulta_reservas."""
    es_hoy = fecha == hoy
    # Una reserva finalizada que todavía cubre noches futuras fue una salida anticipada: ya no ocupa.
    duerme = next(
        (r for r in reservas
         if r.entrada <= fecha < r.salida and not (r.estado == Reserva.FINALIZADA and fecha >= hoy)),
        None,
    )
    sale = next(
        (r for r in reservas
         if (r.salida == fecha and r.estado != Reserva.FINALIZADA)
         or (r.salida < fecha and r.estado == Reserva.EN_CURSO)),
        None,
    )
    sucia = es_hoy and habitacion.estado_limpieza == Habitacion.SUCIA

    if habitacion.fuera_de_servicio:
        return EstadoHabitacion(habitacion, MANTENIMIENTO, fecha, es_hoy=es_hoy, reserva=duerme, duerme=duerme)
    if sale:
        return EstadoHabitacion(habitacion, SALE, fecha, es_hoy=es_hoy, reserva=sale, duerme=duerme,
                                llega_despues=duerme, sucia=sucia)
    if duerme and duerme.estado == Reserva.CONFIRMADA:
        return EstadoHabitacion(habitacion, LLEGA, fecha, es_hoy=es_hoy, reserva=duerme, duerme=duerme, sucia=sucia)
    if duerme:
        return EstadoHabitacion(habitacion, OCUPADA, fecha, es_hoy=es_hoy, reserva=duerme, duerme=duerme, sucia=sucia)
    if sucia:
        return EstadoHabitacion(habitacion, SUCIA, fecha, es_hoy=es_hoy, sucia=True)
    return EstadoHabitacion(habitacion, LIBRE, fecha, es_hoy=es_hoy)


def estados_del_dia(fecha, hoy):
    """El estado de todas las habitaciones, ordenadas por piso y número."""
    habitaciones = db.session.scalars(
        db.select(Habitacion).order_by(Habitacion.piso, Habitacion.numero)
    ).all()
    por_habitacion = defaultdict(list)
    for reserva in db.session.scalars(_consulta_reservas(fecha, hoy)):
        por_habitacion[reserva.habitacion_id].append(reserva)
    return [calcular_estado(h, por_habitacion[h.id], fecha, hoy) for h in habitaciones]


def resumen(estados, fecha):
    """Indicadores del día para la cabecera del plano."""
    habilitadas = sum(1 for e in estados if not e.habitacion.fuera_de_servicio)
    ocupadas = sum(1 for e in estados if e.duerme)
    llegadas = [e.duerme for e in estados if e.duerme and e.duerme.entrada == fecha]
    salidas_hechas = db.session.scalar(
        db.select(db.func.count(Reserva.id)).where(
            Reserva.salida == fecha, Reserva.estado == Reserva.FINALIZADA
        )
    )
    return {
        "habilitadas": habilitadas,
        "ocupadas": ocupadas,
        "porcentaje": round(100 * ocupadas / habilitadas) if habilitadas else 0,
        "llegadas_pendientes": sum(1 for r in llegadas if r.estado == Reserva.CONFIRMADA),
        "llegadas_hechas": sum(1 for r in llegadas if r.estado == Reserva.EN_CURSO),
        "salidas_pendientes": sum(1 for e in estados if e.estado == SALE),
        "salidas_hechas": salidas_hechas,
        "sucias": sum(1 for e in estados if e.sucia),
        "mantenimiento": sum(1 for e in estados if e.estado == MANTENIMIENTO),
    }


def detalle_habitacion(habitacion, fecha, hoy):
    """Todo lo que muestra el panel lateral del plano para una habitación."""
    reservas = db.session.scalars(
        _consulta_reservas(fecha, hoy).where(Reserva.habitacion_id == habitacion.id)
    ).all()
    estado = calcular_estado(habitacion, reservas, fecha, hoy)
    proxima = db.session.scalar(
        db.select(Reserva)
        .where(
            Reserva.habitacion_id == habitacion.id,
            Reserva.estado.notin_(Reserva.INACTIVAS),
            Reserva.entrada > fecha,
        )
        .order_by(Reserva.entrada)
        .limit(1)
    )
    reserva = estado.reserva
    es_hoy = fecha == hoy
    return DetalleHabitacion(
        estado=estado,
        proxima=proxima,
        puede_checkin=es_hoy and estado.estado == LLEGA,
        puede_checkout=es_hoy and reserva is not None and reserva.estado == Reserva.EN_CURSO,
    )
