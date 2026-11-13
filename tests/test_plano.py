from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Habitacion, Reserva
from app.services import ocupacion
from app.services.errores import ErrorDeNegocio
from app.services.recepcion import (
    hacer_checkin,
    hacer_checkout,
    marcar_no_show,
    poner_en_mantenimiento,
)

HOY = date(2026, 10, 14)


def dia(n):
    return HOY + timedelta(days=n)


def estado_en(fecha):
    (estado,) = ocupacion.estados_del_dia(fecha, HOY)
    return estado


def test_sin_reservas_esta_libre(habitacion):
    assert estado_en(HOY).estado == ocupacion.LIBRE


def test_llegada_pendiente(habitacion, reservar):
    reservar(habitacion, HOY, dia(3))
    estado = estado_en(HOY)
    assert estado.estado == ocupacion.LLEGA
    assert estado.etiqueta == "Llega hoy"


def test_huesped_alojado(habitacion, reservar):
    reservar(habitacion, dia(-2), dia(2), Reserva.EN_CURSO)
    assert estado_en(HOY).estado == ocupacion.OCUPADA


def test_el_dia_de_salida_no_es_una_noche_ocupada(habitacion, reservar):
    reservar(habitacion, dia(-3), HOY, Reserva.FINALIZADA)
    estado = estado_en(HOY)
    assert estado.estado == ocupacion.LIBRE
    assert estado.duerme is None


def test_sale_uno_y_llega_otro_el_mismo_dia(habitacion, reservar):
    sale = reservar(habitacion, dia(-3), HOY, Reserva.EN_CURSO)
    llega = reservar(habitacion, HOY, dia(2))
    estado = estado_en(HOY)
    assert estado.estado == ocupacion.SALE
    assert estado.reserva == sale
    assert estado.llega_despues == llega


def test_checkout_deja_sucia_y_bloquea_el_checkin(habitacion, reservar):
    sale = reservar(habitacion, dia(-3), HOY, Reserva.EN_CURSO)
    llega = reservar(habitacion, HOY, dia(2))

    hacer_checkout(sale, HOY)
    assert habitacion.estado_limpieza == Habitacion.SUCIA
    with pytest.raises(ErrorDeNegocio, match="sucia"):
        hacer_checkin(llega, HOY)

    habitacion.estado_limpieza = Habitacion.LIMPIA
    hacer_checkin(llega, HOY)
    assert llega.estado == Reserva.EN_CURSO


def test_salida_anticipada_libera_las_noches_siguientes(habitacion, reservar):
    reserva = reservar(habitacion, dia(-2), dia(3), Reserva.EN_CURSO)
    hacer_checkout(reserva, HOY)
    db.session.commit()
    assert reserva.salida == HOY
    assert estado_en(dia(1)).estado == ocupacion.LIBRE


def test_api_rechaza_checkin_con_habitacion_sucia(cliente, habitacion, reservar):
    hoy = date.today()
    reserva = reservar(habitacion, hoy, hoy + timedelta(days=2))
    habitacion.estado_limpieza = Habitacion.SUCIA
    db.session.commit()

    respuesta = cliente.post(f"/administracion/api/reservas/{reserva.id}/check-in", json={})
    assert respuesta.status_code == 409
    assert "sucia" in respuesta.get_json()["error"]


def test_api_exige_json(cliente, habitacion):
    respuesta = cliente.post(f"/administracion/api/habitaciones/{habitacion.id}/limpieza", data={"estado": "sucia"})
    assert respuesta.status_code == 415


def test_el_plano_se_renderiza(cliente, habitacion, reservar):
    hoy = date.today()
    reservar(habitacion, hoy - timedelta(days=1), hoy + timedelta(days=2), Reserva.EN_CURSO)
    respuesta = cliente.get("/administracion/")
    assert respuesta.status_code == 200
    assert "Rossi" in respuesta.get_data(as_text=True)

    panel = cliente.get(f"/administracion/plano/habitaciones/{habitacion.id}")
    assert "Hacer check-out" in panel.get_data(as_text=True)


def test_llegada_atrasada(habitacion, reservar):
    reservar(habitacion, dia(-1), dia(2))
    estado = estado_en(HOY)
    assert estado.estado == ocupacion.LLEGA
    assert estado.etiqueta == "Atrasada"


def test_no_show_libera_la_habitacion(habitacion, reservar):
    reserva = reservar(habitacion, dia(-1), dia(2))
    marcar_no_show(reserva, HOY)
    db.session.commit()
    assert estado_en(HOY).estado == ocupacion.LIBRE


def test_no_show_no_se_puede_antes_de_la_llegada(habitacion, reservar):
    reserva = reservar(habitacion, dia(2), dia(4))
    with pytest.raises(ErrorDeNegocio):
        marcar_no_show(reserva, HOY)


def test_mantenimiento_devuelve_las_reservas_a_reubicar(habitacion, reservar):
    proxima = reservar(habitacion, dia(3), dia(5))
    assert poner_en_mantenimiento(habitacion, "Pintura", HOY) == [proxima]
    assert habitacion.fuera_de_servicio


def test_mantenimiento_sin_reservas_cercanas(habitacion, reservar):
    reservar(habitacion, dia(20), dia(22))
    assert poner_en_mantenimiento(habitacion, "Pintura", HOY) == []
    assert habitacion.fuera_de_servicio


def test_mantenimiento_con_huesped_alojado_no_se_puede(habitacion, reservar):
    reservar(habitacion, dia(-1), dia(2), Reserva.EN_CURSO)
    with pytest.raises(ErrorDeNegocio, match="huésped alojado"):
        poner_en_mantenimiento(habitacion, "Pintura", HOY)


def test_api_de_mantenimiento_avisa_las_reservas(cliente, habitacion, reservar):
    hoy = date.today()
    reservar(habitacion, hoy + timedelta(days=1), hoy + timedelta(days=3))
    url = f"/administracion/api/habitaciones/{habitacion.id}/mantenimiento"
    respuesta = cliente.post(url, json={"activo": True, "nota": "Pintura"})
    assert respuesta.status_code == 200
    assert "Tiene 1 reserva" in respuesta.get_json()["mensaje"]
