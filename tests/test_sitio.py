from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Habitacion, Reserva, TipoHabitacion


@pytest.fixture
def tipo(app):
    tipo = TipoHabitacion(nombre="Doble superior", capacidad=2, tarifa_base=56000, slug="doble-superior",
                          metros=20, comodidades="Cama queen\nEscritorio",
                          imagen="tipo-doble-superior.png", modelo="tipo-doble-superior.glb")
    db.session.add_all([Habitacion(numero="201", piso=2, tipo=tipo), Habitacion(numero="202", piso=2, tipo=tipo)])
    db.session.commit()
    return tipo


def datos_reserva(**cambios):
    hoy = date.today()
    datos = {
        "tipo": "doble-superior",
        "entrada": (hoy + timedelta(days=3)).isoformat(),
        "salida": (hoy + timedelta(days=6)).isoformat(),
        "personas": "2",
        "nombre": "Lucía Fernández",
        "email": "",
    }
    datos.update(cambios)
    return datos


def test_el_inicio_no_pide_login(anonimo, tipo):
    html = anonimo.get("/").get_data(as_text=True)
    assert "Doble superior" in html
    assert "$ 56.000" in html


def test_detalle_con_visor_3d(anonimo, tipo):
    html = anonimo.get("/habitaciones/doble-superior").get_data(as_text=True)
    assert 'src="/media/tipo-doble-superior.glb"' in html
    assert 'poster="/media/tipo-doble-superior.png"' in html
    assert "Cama queen" in html
    assert anonimo.get("/habitaciones/no-existe").status_code == 404


def test_detalle_solo_con_foto_no_carga_el_visor(anonimo, tipo):
    tipo.modelo = None
    db.session.commit()
    html = anonimo.get("/habitaciones/doble-superior").get_data(as_text=True)
    assert "<model-viewer" not in html
    assert "model-viewer.min.js" not in html
    assert 'class="visor__imagen" src="/media/tipo-doble-superior.png"' in html


def test_los_tipos_sin_habitaciones_no_se_ofrecen(anonimo, tipo):
    db.session.add(TipoHabitacion(nombre="Suite nueva", capacidad=4, tarifa_base=90000, slug="suite-nueva"))
    db.session.commit()
    assert "Suite nueva" not in anonimo.get("/").get_data(as_text=True)


def test_reservar_crea_la_reserva_y_asigna_habitacion(anonimo, tipo):
    respuesta = anonimo.post("/reservar", data=datos_reserva())
    assert respuesta.status_code == 302

    reserva = db.session.scalar(db.select(Reserva))
    assert reserva.habitacion.numero == "201"
    assert reserva.estado == Reserva.CONFIRMADA
    assert reserva.total == 3 * 56000
    assert (reserva.huesped.nombre, reserva.huesped.apellido) == ("Lucía", "Fernández")

    html = anonimo.get(respuesta.location).get_data(as_text=True)
    assert "¡Listo, Lucía!" in html
    assert reserva.codigo in html


def test_si_la_primera_esta_ocupada_usa_la_siguiente(anonimo, tipo):
    anonimo.post("/reservar", data=datos_reserva())
    anonimo.post("/reservar", data=datos_reserva(nombre="Martín Sosa"))
    numeros = sorted(r.habitacion.numero for r in db.session.scalars(db.select(Reserva)))
    assert numeros == ["201", "202"]


def test_sin_lugar_muestra_el_aviso(anonimo, tipo):
    anonimo.post("/reservar", data=datos_reserva())
    anonimo.post("/reservar", data=datos_reserva(nombre="Martín Sosa"))
    respuesta = anonimo.post("/reservar", data=datos_reserva(nombre="Ana Rossi"))
    assert respuesta.status_code == 422
    assert "No queda lugar en la Doble superior" in respuesta.get_data(as_text=True)


@pytest.mark.parametrize("cambios, mensaje", [
    ({"personas": "3"}, "es para 2 personas"),
    ({"nombre": "Lucía"}, "nombre y apellido"),
    ({"entrada": (date.today() - timedelta(days=1)).isoformat()}, "anterior a hoy"),
    ({"salida": date.today().isoformat()}, "posterior a la llegada"),
])
def test_validaciones(anonimo, tipo, cambios, mensaje):
    respuesta = anonimo.post("/reservar", data=datos_reserva(**cambios))
    assert respuesta.status_code == 422
    assert mensaje in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(Reserva)) is None


def test_confirmacion_inexistente(anonimo):
    assert anonimo.get("/reserva/no-existe").status_code == 404
