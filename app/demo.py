"""Comando `flask --app app demo`: carga el hotel de ejemplo "Hotel Mirador".

Genera habitaciones, huéspedes y reservas alrededor de la fecha de hoy, así el plano
siempre tiene movimiento (llegadas, salidas, habitaciones sucias, una en mantenimiento).
"""
import random
import shutil
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.models import ConfiguracionHotel, Habitacion, Huesped, Reserva, TipoHabitacion, Usuario

TIPOS = [
    ("Simple", 1, 38000),
    ("Doble estándar", 2, 48000),
    ("Doble superior", 2, 56000),
    ("Suite Mirador", 4, 92000),
]
# Tipo según la posición de la habitación en el piso (01 a 08)
DISTRIBUCION = ["Doble estándar"] * 3 + ["Simple"] + ["Doble superior"] * 3 + ["Suite Mirador"]
PISOS = 3

NOMBRES = [
    "Lucía", "Martín", "Sofía", "Juan", "Valentina", "Mateo", "Camila", "Santiago", "Julieta", "Tomás",
    "Florencia", "Nicolás", "Agustina", "Facundo", "Micaela", "Joaquín", "Carolina", "Ignacio", "Paula",
    "Federico", "Daniela", "Gonzalo", "Romina", "Diego", "Marina", "Pablo", "Victoria", "Andrés", "Lara",
    "Emiliano", "Ana", "Bruno", "Mercedes", "Leandro", "Rocío", "Hernán",
]
APELLIDOS = [
    "Fernández", "García", "Rodríguez", "González", "López", "Martínez", "Pérez", "Gómez", "Sánchez",
    "Romero", "Sosa", "Torres", "Álvarez", "Ruiz", "Ramírez", "Flores", "Benítez", "Acosta", "Medina",
    "Herrera", "Suárez", "Aguirre", "Giménez", "Gutiérrez", "Pereyra", "Rojas", "Molina", "Castro",
    "Ortiz", "Silva", "Núñez", "Luna", "Juárez", "Cabrera", "Ríos", "Morales", "Ibarra", "Duarte",
    "Rossi", "Mendoza",
]
PAISES = ["AR"] * 14 + ["UY", "UY", "CL", "CL", "BR", "BR", "PY", "US", "ES", "DE"]
NOTAS = [
    "Pidió cuna para bebé.",
    "Late check-out a las 11:30 si se puede.",
    "Aniversario: dejar una botella de espumante en la habitación.",
    "Llega en el vuelo de la noche, alrededor de las 23.",
    "Viaja con un perro chico.",
    "Necesita factura A a nombre de la empresa.",
    "Celíaca: avisar en el desayuno.",
    "Reservó cochera cubierta.",
]
HABITACION_EN_MANTENIMIENTO = ("107", "Pierde agua el aire acondicionado")
# Usuarios de prueba (nombre, email, contraseña, rol). Se muestran en la pantalla de login.
USUARIOS_DEMO = [
    ("Sofía Martínez", "admin@mirador.demo", "admin123", Usuario.ADMIN),
    ("Martín Gómez", "recepcion@mirador.demo", "recepcion123", Usuario.RECEPCION),
]


def _sin_tildes(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _huesped(rnd):
    nombre, apellido = rnd.choice(NOMBRES), rnd.choice(APELLIDOS)
    pais = rnd.choice(PAISES)
    if pais == "AR":
        documento = str(rnd.randint(20_000_000, 45_000_000))
        telefono = f"+54 9 294 {rnd.randint(400, 499)}-{rnd.randint(1000, 9999)}"
    else:
        documento = f"{rnd.choice('ABCFGKLX')}{rnd.choice('ABCDEFGH')}{rnd.randint(100000, 999999)}"
        telefono = f"+{rnd.randint(1, 98)} {rnd.randint(100, 999)} {rnd.randint(100000, 999999)}"
    return Huesped(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        email=f"{_sin_tildes(nombre)}.{_sin_tildes(apellido)}@example.com",
        telefono=telefono,
        pais=pais,
    )


def _estado_reserva(rnd, entrada, salida, hoy):
    if salida < hoy:
        return Reserva.FINALIZADA
    if salida == hoy:
        return Reserva.EN_CURSO if rnd.random() < 0.7 else Reserva.FINALIZADA
    if entrada < hoy:
        return Reserva.EN_CURSO
    if entrada == hoy:
        return Reserva.CONFIRMADA if rnd.random() < 0.7 else Reserva.EN_CURSO
    return Reserva.CONFIRMADA


def _pagado(rnd, estado, total):
    if estado == Reserva.FINALIZADA:
        return total
    if estado == Reserva.EN_CURSO:
        return rnd.choice([total, total, total // 2])
    return rnd.choice([0, 0, total // 2, total])


def cargar_demo(hoy, semilla=7):
    rnd = random.Random(semilla)

    # Logo del hotel demo: se copia a instance/uploads/ como si lo hubiera subido el hotel
    origen = Path(current_app.root_path).parent / "design" / "identidad" / "hotel-demo" / "logo-hotel-mirador.svg"
    logo = None
    if origen.exists():
        logo = origen.name
        shutil.copy(origen, Path(current_app.instance_path) / "uploads" / logo)

    db.session.add(ConfiguracionHotel(
        nombre="Hotel Mirador",
        logo=logo,
        color_acento="#1F6F5C",
        ciudad="San Carlos de Bariloche",
        moneda="$",
        hora_checkin="14:00",
        hora_checkout="10:00",
        setup_completo=True,
    ))

    for nombre, email, password, rol in USUARIOS_DEMO:
        usuario = Usuario(nombre=nombre, email=email, rol=rol)
        usuario.set_password(password)
        db.session.add(usuario)

    tipos = {nombre: TipoHabitacion(nombre=nombre, capacidad=cap, tarifa_base=tarifa) for nombre, cap, tarifa in TIPOS}
    db.session.add_all(tipos.values())

    habitaciones = []
    for piso in range(1, PISOS + 1):
        for posicion, tipo in enumerate(DISTRIBUCION, start=1):
            habitaciones.append(Habitacion(numero=f"{piso}{posicion:02d}", piso=piso, tipo=tipos[tipo]))
    db.session.add_all(habitaciones)

    huespedes = [_huesped(rnd) for _ in range(80)]
    db.session.add_all(huespedes)

    desde, hasta = hoy - timedelta(days=30), hoy + timedelta(days=45)
    numero_bloqueada, nota_bloqueada = HABITACION_EN_MANTENIMIENTO
    for habitacion in habitaciones:
        bloqueada = habitacion.numero == numero_bloqueada
        dia = desde + timedelta(days=rnd.randint(0, 4))
        while dia < hasta:
            noches = rnd.choice([1, 2, 2, 3, 3, 4, 5, 7])
            entrada, salida = dia, dia + timedelta(days=noches)
            dia = salida + timedelta(days=rnd.choice([0, 0, 1, 1, 2, 3, 5]))
            # La habitación en mantenimiento no tiene reservas estos días
            if bloqueada and entrada <= hoy + timedelta(days=4) and salida >= hoy - timedelta(days=1):
                continue
            estado = _estado_reserva(rnd, entrada, salida, hoy)
            total = noches * habitacion.tipo.tarifa_base
            db.session.add(Reserva(
                huesped=rnd.choice(huespedes),
                habitacion=habitacion,
                entrada=entrada,
                salida=salida,
                personas=rnd.randint(1, habitacion.tipo.capacidad),
                estado=estado,
                total=total,
                pagado=_pagado(rnd, estado, total),
                notas=rnd.choice(NOTAS) if rnd.random() < 0.25 else None,
            ))
            # Si ya hizo el check-out hoy, la habitación quedó para limpiar
            if estado == Reserva.FINALIZADA and salida == hoy:
                habitacion.estado_limpieza = Habitacion.SUCIA

        if bloqueada:
            habitacion.fuera_de_servicio = True
            habitacion.nota_mantenimiento = nota_bloqueada
        elif rnd.random() < 0.15:
            habitacion.estado_limpieza = Habitacion.SUCIA

    db.session.commit()


@click.command("demo")
@click.option("--si", is_flag=True, help="No pedir confirmación.")
@with_appcontext
def demo_command(si):
    """Borra la base y carga el Hotel Mirador de ejemplo."""
    if not si:
        click.confirm("Esto borra la base de datos y carga el Hotel Mirador de ejemplo. ¿Seguir?", abort=True)
    db.drop_all()
    db.create_all()
    cargar_demo(date.today())
    habitaciones = db.session.scalar(db.select(db.func.count(Habitacion.id)))
    reservas = db.session.scalar(db.select(db.func.count(Reserva.id)))
    click.echo(f"Listo: Hotel Mirador con {habitaciones} habitaciones y {reservas} reservas.")
