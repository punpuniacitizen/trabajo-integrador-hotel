from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Habitacion, Reserva, TipoHabitacion
from app.services.errores import ErrorDeNegocio
from app.services.reservas import mover_reserva, reserva_superpuesta

HOY = date(2026, 10, 14)


def dia(n):
    return HOY + timedelta(days=n)


@pytest.fixture
def suite(app):
    tipo = TipoHabitacion(nombre="Suite", capacidad=4, tarifa_base=90000)
    habitacion = Habitacion(numero="201", piso=2, tipo=tipo)
    db.session.add(habitacion)
    db.session.commit()
    return habitacion


def test_salir_y_entrar_el_mismo_dia_no_se_superpone(habitacion, reservar):
    reservar(habitacion, dia(0), dia(3))
    assert reserva_superpuesta(habitacion, dia(3), dia(5)) is None
    assert reserva_superpuesta(habitacion, dia(2), dia(5)) is not None


def test_mover_de_fecha_y_habitacion_recalcula_el_total(habitacion, suite, reservar):
    reserva = reservar(habitacion, dia(2), dia(4))
    mover_reserva(reserva, suite, dia(5), dia(8), HOY)
    assert reserva.habitacion == suite
    assert (reserva.entrada, reserva.salida) == (dia(5), dia(8))
    assert reserva.total == 3 * 90000


def test_no_se_puede_mover_sobre_otra_reserva(habitacion, suite, reservar):
    reservar(suite, dia(3), dia(6))
    reserva = reservar(habitacion, dia(2), dia(4))
    with pytest.raises(ErrorDeNegocio, match="ya está reservada"):
        mover_reserva(reserva, suite, dia(2), dia(4), HOY)


def test_no_se_puede_mover_a_una_habitacion_chica(habitacion, suite, reservar):
    reserva = reservar(suite, dia(2), dia(4))
    reserva.personas = 3
    with pytest.raises(ErrorDeNegocio, match="es para 2 personas"):
        mover_reserva(reserva, habitacion, dia(2), dia(4), HOY)


def test_no_se_puede_mover_al_pasado(habitacion, reservar):
    reserva = reservar(habitacion, dia(2), dia(4))
    with pytest.raises(ErrorDeNegocio, match="pasado"):
        mover_reserva(reserva, habitacion, dia(-1), dia(1), HOY)


def test_alojado_puede_cambiar_de_habitacion_pero_no_la_entrada(habitacion, suite, reservar):
    reserva = reservar(habitacion, dia(-2), dia(2), Reserva.EN_CURSO)
    with pytest.raises(ErrorDeNegocio, match="check-in"):
        mover_reserva(reserva, habitacion, dia(-1), dia(2), HOY)

    mover_reserva(reserva, suite, dia(-2), dia(4), HOY)
    assert reserva.habitacion == suite
    assert habitacion.estado_limpieza == Habitacion.SUCIA  # la que dejó hay que limpiarla


def test_api_mover(cliente, habitacion, suite, reservar):
    hoy = date.today()
    reserva = reservar(habitacion, hoy + timedelta(days=1), hoy + timedelta(days=3))
    respuesta = cliente.post(
        f"/administracion/api/reservas/{reserva.id}/mover",
        json={
            "habitacion_id": suite.id,
            "entrada": (hoy + timedelta(days=2)).isoformat(),
            "salida": (hoy + timedelta(days=5)).isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert "Nuevo total" in respuesta.get_json()["mensaje"]


def test_api_mover_con_datos_invalidos(cliente, habitacion, reservar):
    reserva = reservar(habitacion, date.today(), date.today() + timedelta(days=2))
    respuesta = cliente.post(f"/administracion/api/reservas/{reserva.id}/mover", json={"entrada": "ayer"})
    assert respuesta.status_code == 409


def test_el_tape_chart_se_renderiza(cliente, habitacion, reservar):
    hoy = date.today()
    reservar(habitacion, hoy - timedelta(days=1), hoy + timedelta(days=2), Reserva.EN_CURSO)
    html = cliente.get("/administracion/reservas/?dias=30").get_data(as_text=True)
    assert "Rossi · 3 n" in html
    # Entra la tarde de ayer (columna 3 + 2*2 = 7) y sale la mañana de pasado mañana (3 + 2*5 = 13)
    assert "grid-column: 7 / 13" in html
