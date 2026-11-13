"""Operaciones de recepción: check-in, check-out, limpieza y mantenimiento.

Las funciones modifican los objetos y validan las reglas; el commit lo hace la ruta.
"""
from datetime import timedelta

from app.extensions import db
from app.filtros import fecha_corta
from app.models import Habitacion, Reserva
from app.services.errores import ErrorDeNegocio

# Al bloquear una habitación se avisa de las reservas de estos próximos días
DIAS_AVISO_MANTENIMIENTO = 7


def huesped_alojado(habitacion):
    return db.session.scalar(
        db.select(Reserva)
        .where(Reserva.habitacion_id == habitacion.id, Reserva.estado == Reserva.EN_CURSO)
        .limit(1)
    )


def hacer_checkin(reserva, hoy):
    habitacion = reserva.habitacion
    if reserva.estado != Reserva.CONFIRMADA:
        raise ErrorDeNegocio("Esta reserva no está pendiente de check-in.")
    if reserva.entrada > hoy:
        raise ErrorDeNegocio(
            f"La reserva empieza el {fecha_corta(reserva.entrada)}: todavía no se puede hacer el check-in."
        )
    if habitacion.fuera_de_servicio:
        raise ErrorDeNegocio(f"La {habitacion.numero} está en mantenimiento.")
    if huesped_alojado(habitacion):
        raise ErrorDeNegocio(f"Todavía hay un huésped en la {habitacion.numero}. Hacé primero su check-out.")
    if habitacion.estado_limpieza == Habitacion.SUCIA:
        raise ErrorDeNegocio(f"La {habitacion.numero} está sucia. Marcala como limpia antes del check-in.")
    reserva.estado = Reserva.EN_CURSO


def hacer_checkout(reserva, hoy):
    if reserva.estado != Reserva.EN_CURSO:
        raise ErrorDeNegocio("Esta reserva no tiene un huésped alojado.")
    # Salida anticipada: se acorta la estadía para liberar las noches que quedaban.
    # El total no se recalcula; eso queda a criterio del hotel.
    if reserva.entrada < hoy < reserva.salida:
        reserva.salida = hoy
    reserva.estado = Reserva.FINALIZADA
    reserva.habitacion.estado_limpieza = Habitacion.SUCIA


def marcar_no_show(reserva, hoy):
    """El huésped no se presentó: la reserva deja de ocupar la habitación."""
    if reserva.estado != Reserva.CONFIRMADA:
        raise ErrorDeNegocio("Esta reserva no está pendiente de llegada.")
    if reserva.entrada > hoy:
        raise ErrorDeNegocio(f"La reserva empieza el {fecha_corta(reserva.entrada)}: todavía no se puede marcar como no presentada.")
    reserva.estado = Reserva.NO_SHOW


def marcar_limpieza(habitacion, estado):
    if estado not in (Habitacion.LIMPIA, Habitacion.SUCIA):
        raise ErrorDeNegocio("Estado de limpieza inválido.")
    habitacion.estado_limpieza = estado


def reservas_por_llegar(habitacion, hoy):
    """Reservas confirmadas de la habitación que se superponen con los próximos días."""
    limite = hoy + timedelta(days=DIAS_AVISO_MANTENIMIENTO)
    return db.session.scalars(
        db.select(Reserva)
        .where(
            Reserva.habitacion_id == habitacion.id,
            Reserva.estado == Reserva.CONFIRMADA,
            Reserva.entrada < limite,
            Reserva.salida > hoy,
        )
        .order_by(Reserva.entrada)
    ).all()


def poner_en_mantenimiento(habitacion, nota, hoy):
    """Bloquea la habitación. Devuelve las reservas de los próximos días que hay que reubicar."""
    if huesped_alojado(habitacion):
        raise ErrorDeNegocio(
            f"Hay un huésped alojado en la {habitacion.numero}. "
            "Hacé el check-out o cambialo de habitación antes de bloquearla."
        )
    habitacion.fuera_de_servicio = True
    habitacion.nota_mantenimiento = nota or None
    return reservas_por_llegar(habitacion, hoy)


def quitar_de_mantenimiento(habitacion):
    habitacion.fuera_de_servicio = False
    habitacion.nota_mantenimiento = None
