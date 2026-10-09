"""Reglas de la configuración: tipos de habitación, habitaciones (y pisos) y usuarios.

Los pisos no son una tabla aparte: un piso existe mientras tenga habitaciones.
"""
import re
import unicodedata
from datetime import date

from app.extensions import db
from app.models import Habitacion, Reserva, TipoHabitacion, Usuario
from app.services.errores import ErrorDeNegocio

MAXIMO_POR_TANDA = 50
MAXIMO_PISO = 99
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


# --- Tipos de habitación ---------------------------------------------------------

def slug_unico(nombre, excluir=None):
    """"Suite Mirador" -> "suite-mirador" (con -2, -3… si ya existe)."""
    ascii_ = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_).strip("-") or "habitacion"
    slug, n = base, 2
    while True:
        otro = db.session.scalar(db.select(TipoHabitacion).where(TipoHabitacion.slug == slug))
        if otro is None or otro is excluir:
            return slug
        slug, n = f"{base}-{n}", n + 1


def validar_tipo(nombre, capacidad, tarifa, metros, excluir=None):
    if not nombre:
        raise ErrorDeNegocio("Poné un nombre para el tipo de habitación.")
    repetido = db.session.scalar(
        db.select(TipoHabitacion).where(db.func.lower(TipoHabitacion.nombre) == nombre.lower())
    )
    if repetido is not None and repetido is not excluir:
        raise ErrorDeNegocio(f"Ya existe un tipo llamado «{repetido.nombre}».")
    if capacidad is None or not 1 <= capacidad <= 20:
        raise ErrorDeNegocio("La capacidad tiene que ser de 1 a 20 personas.")
    if tarifa is None or tarifa <= 0:
        raise ErrorDeNegocio("La tarifa por noche tiene que ser mayor a cero.")
    if metros is not None and not 1 <= metros <= 1000:
        raise ErrorDeNegocio("Los metros cuadrados tienen que estar entre 1 y 1000.")


def eliminar_tipo(tipo):
    cantidad = len(tipo.habitaciones)
    if cantidad:
        texto = "1 habitación" if cantidad == 1 else f"{cantidad} habitaciones"
        raise ErrorDeNegocio(f"Hay {texto} de este tipo. Pasalas a otro tipo o borralas antes.")
    db.session.delete(tipo)


# --- Pisos y habitaciones -----------------------------------------------------------

def proxima_posicion(piso):
    """La siguiente posición libre en el piso: con 101 a 108 cargadas, devuelve 9."""
    numeros = db.session.scalars(db.select(Habitacion.numero).where(Habitacion.piso == piso))
    posiciones = [int(n[len(str(piso)):]) for n in numeros
                  if n.startswith(str(piso)) and n[len(str(piso)):].isdigit()]
    return max(posiciones, default=0) + 1


def agregar_habitaciones(piso, cantidad, tipo, desde=None):
    """Crea `cantidad` habitaciones en el piso, numeradas piso + posición (201, 202…)."""
    if piso is None or not 1 <= piso <= MAXIMO_PISO:
        raise ErrorDeNegocio(f"El piso tiene que ser un número de 1 a {MAXIMO_PISO}.")
    if cantidad is None or not 1 <= cantidad <= MAXIMO_POR_TANDA:
        raise ErrorDeNegocio(f"Se pueden agregar de 1 a {MAXIMO_POR_TANDA} habitaciones por vez.")
    if tipo is None:
        raise ErrorDeNegocio("Elegí el tipo de las habitaciones nuevas.")
    desde = desde or proxima_posicion(piso)
    if desde < 1 or desde + cantidad - 1 > 99:
        raise ErrorDeNegocio("La numeración dentro del piso va de 01 a 99.")

    numeros = [f"{piso}{posicion:02d}" for posicion in range(desde, desde + cantidad)]
    existentes = sorted(db.session.scalars(db.select(Habitacion.numero).where(Habitacion.numero.in_(numeros))))
    if existentes:
        raise ErrorDeNegocio(f"Ya existen: {', '.join(existentes)}. Elegí otra numeración.")

    nuevas = [Habitacion(numero=numero, piso=piso, tipo=tipo) for numero in numeros]
    db.session.add_all(nuevas)
    return nuevas


def cambiar_tipo(habitacion, tipo, hoy=None):
    hoy = hoy or date.today()
    excede = db.session.scalar(
        db.select(Reserva).where(
            Reserva.habitacion_id == habitacion.id,
            Reserva.estado.notin_(Reserva.INACTIVAS),
            Reserva.salida >= hoy,
            Reserva.personas > tipo.capacidad,
        ).limit(1)
    )
    if excede:
        raise ErrorDeNegocio(
            f"La {habitacion.numero} tiene una reserva de {excede.personas} personas y una "
            f"{tipo.nombre} es para {tipo.capacidad}."
        )
    habitacion.tipo = tipo


def eliminar_habitacion(habitacion):
    if habitacion.reservas:
        raise ErrorDeNegocio(
            f"La {habitacion.numero} tiene reservas cargadas y no se puede borrar. "
            "Si no se usa más, ponela en mantenimiento desde el plano."
        )
    db.session.delete(habitacion)


# --- Usuarios ----------------------------------------------------------------------------

def crear_usuario(nombre, email, rol, password):
    nombre, email = " ".join(nombre.split()), email.strip().lower()
    if not nombre:
        raise ErrorDeNegocio("Poné el nombre del usuario.")
    if not EMAIL.fullmatch(email):
        raise ErrorDeNegocio("El email no es válido.")
    if db.session.scalar(db.select(Usuario).where(Usuario.email == email)):
        raise ErrorDeNegocio(f"Ya hay un usuario con el email {email}.")
    if rol not in (Usuario.ADMIN, Usuario.RECEPCION):
        raise ErrorDeNegocio("Elegí un rol.")
    if len(password) < 6:
        raise ErrorDeNegocio("La contraseña tiene que tener al menos 6 caracteres.")
    usuario = Usuario(nombre=nombre, email=email, rol=rol)
    usuario.set_password(password)
    db.session.add(usuario)
    return usuario


def eliminar_usuario(usuario, actual):
    if usuario.id == actual.id:
        raise ErrorDeNegocio("No podés borrar tu propio usuario.")
    if usuario.rol == Usuario.ADMIN:
        admins = db.session.scalar(db.select(db.func.count(Usuario.id)).where(Usuario.rol == Usuario.ADMIN))
        if admins <= 1:
            raise ErrorDeNegocio("Tiene que quedar al menos un usuario de administración.")
    db.session.delete(usuario)
