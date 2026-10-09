"""Reglas de las reservas: disponibilidad, capacidad y cambios de fecha o de habitación."""
import secrets

from app.extensions import db
from app.filtros import rango_fechas
from app.models import Habitacion, Huesped, Reserva
from app.services.errores import ErrorDeNegocio

# Para que el demostrador no permita estadías absurdas
MAXIMO_NOCHES_WEB = 30


def reserva_superpuesta(habitacion, entrada, salida, excluir=None):
    """La primera reserva activa de la habitación que pisa esas noches (o None).

    Dos estadías no se pisan si una sale el mismo día que entra la otra.
    """
    consulta = db.select(Reserva).where(
        Reserva.habitacion_id == habitacion.id,
        Reserva.estado.notin_(Reserva.INACTIVAS),
        Reserva.entrada < salida,
        Reserva.salida > entrada,
    )
    if excluir is not None:
        consulta = consulta.where(Reserva.id != excluir.id)
    return db.session.scalar(consulta.order_by(Reserva.entrada).limit(1))


def calcular_total(tipo, entrada, salida):
    return (salida - entrada).days * tipo.tarifa_base


def validar_disponibilidad(habitacion, entrada, salida, personas, excluir=None):
    if salida <= entrada:
        raise ErrorDeNegocio("La salida tiene que ser posterior a la entrada.")
    if habitacion.fuera_de_servicio:
        raise ErrorDeNegocio(f"La {habitacion.numero} está en mantenimiento.")
    capacidad = habitacion.tipo.capacidad
    if personas > capacidad:
        texto = "1 persona" if capacidad == 1 else f"{capacidad} personas"
        raise ErrorDeNegocio(f"La {habitacion.numero} es para {texto} y la reserva es de {personas}.")
    otra = reserva_superpuesta(habitacion, entrada, salida, excluir)
    if otra:
        raise ErrorDeNegocio(
            f"La {habitacion.numero} ya está reservada del {rango_fechas(otra.entrada, otra.salida)} "
            f"({otra.huesped.apellido})."
        )


def mover_reserva(reserva, habitacion, entrada, salida, hoy):
    """Cambia la habitación y/o las fechas de una reserva (lo usa el tape chart al arrastrar)."""
    if reserva.estado not in (Reserva.CONFIRMADA, Reserva.EN_CURSO):
        raise ErrorDeNegocio("Solo se pueden cambiar reservas confirmadas o en curso.")
    if reserva.estado == Reserva.EN_CURSO:
        if entrada != reserva.entrada:
            raise ErrorDeNegocio("El huésped ya hizo el check-in: la fecha de entrada no se puede cambiar.")
        if salida < hoy:
            raise ErrorDeNegocio("La salida no puede quedar en el pasado.")
    elif entrada < hoy:
        raise ErrorDeNegocio("La entrada no puede quedar en el pasado.")

    validar_disponibilidad(habitacion, entrada, salida, reserva.personas, excluir=reserva)

    # Si un huésped alojado cambia de habitación, la que deja hay que limpiarla
    if reserva.estado == Reserva.EN_CURSO and habitacion.id != reserva.habitacion_id:
        reserva.habitacion.estado_limpieza = Habitacion.SUCIA

    reserva.habitacion = habitacion
    reserva.entrada = entrada
    reserva.salida = salida
    reserva.total = calcular_total(habitacion.tipo, entrada, salida)


def habitacion_libre(tipo, entrada, salida):
    """La primera habitación de ese tipo libre en esas fechas (o None)."""
    habitaciones = db.session.scalars(
        db.select(Habitacion)
        .where(Habitacion.tipo_id == tipo.id, Habitacion.fuera_de_servicio.is_(False))
        .order_by(Habitacion.piso, Habitacion.numero)
    )
    return next((h for h in habitaciones if reserva_superpuesta(h, entrada, salida) is None), None)


def crear_reserva_web(tipo, entrada, salida, personas, nombre, email, hoy):
    """Reserva hecha por un cliente desde el sitio público.

    Es un demostrador: no hay pago. El sistema elige la habitación y la reserva queda
    confirmada, con todo el saldo a pagar en el hotel.
    """
    nombre = " ".join((nombre or "").split())
    if " " not in nombre:
        raise ErrorDeNegocio("Poné tu nombre y apellido.")
    if entrada < hoy:
        raise ErrorDeNegocio("La llegada no puede ser anterior a hoy.")
    if salida <= entrada:
        raise ErrorDeNegocio("La salida tiene que ser posterior a la llegada.")
    if (salida - entrada).days > MAXIMO_NOCHES_WEB:
        raise ErrorDeNegocio(f"Desde la web se puede reservar hasta {MAXIMO_NOCHES_WEB} noches.")
    if not 1 <= personas <= tipo.capacidad:
        texto = "1 persona" if tipo.capacidad == 1 else f"{tipo.capacidad} personas"
        raise ErrorDeNegocio(f"La {tipo.nombre} es para {texto}. Elegí otra habitación.")

    habitacion = habitacion_libre(tipo, entrada, salida)
    if habitacion is None:
        raise ErrorDeNegocio(
            f"No queda lugar en la {tipo.nombre} para esas fechas. Probá con otras fechas u otra habitación."
        )

    # "Lucía Fernández" -> nombre "Lucía", apellido "Fernández"
    nombres, apellido = nombre.rsplit(" ", 1)
    huesped = Huesped(nombre=nombres, apellido=apellido, email=(email or "").strip() or None)
    reserva = Reserva(
        huesped=huesped,
        habitacion=habitacion,
        entrada=entrada,
        salida=salida,
        personas=personas,
        estado=Reserva.CONFIRMADA,
        total=calcular_total(tipo, entrada, salida),
        pagado=0,
        notas="Reserva hecha desde el sitio web.",
        token=secrets.token_urlsafe(9),
    )
    db.session.add(reserva)
    return reserva
