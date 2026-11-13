from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Habitacion, Huesped, Reserva, TipoHabitacion
from app.services import huespedes
from app.services.errores import ErrorDeNegocio
from app.services.reservas import crear_reserva, disponibilidad

HOY = date(2026, 10, 14)
URL = "/administracion/reservas/nueva"


def dia(n, desde=HOY):
    return desde + timedelta(days=n)


@pytest.fixture
def simple(app):
    tipo = TipoHabitacion(nombre="Simple", capacidad=1, tarifa_base=30000)
    habitacion = Habitacion(numero="102", piso=1, tipo=tipo)
    db.session.add(habitacion)
    db.session.commit()
    return habitacion


def huesped_nuevo():
    return Huesped(nombre="Lucía", apellido="Fernández")


# --- Servicio ------------------------------------------------------------------------------

def test_disponibilidad_marca_por_que_no_se_puede(habitacion, simple, reservar):
    reservar(habitacion, dia(1), dia(3))
    estados = {o.habitacion.numero: o.estado for o in disponibilidad(dia(2), dia(4), 2)}
    assert estados == {"101": "ocupada", "102": "capacidad"}
    simple.fuera_de_servicio = True
    estados = {o.habitacion.numero: (o.estado, o.motivo) for o in disponibilidad(dia(3), dia(4), 1)}
    assert estados == {"101": ("libre", None), "102": ("mantenimiento", "Mantenimiento")}


def test_crear_reserva_calcula_el_total(habitacion):
    reserva = crear_reserva(habitacion, huesped_nuevo(), dia(2), dia(5), 2, HOY, pagado=50000, notas=" Llega tarde ")
    assert reserva.estado == Reserva.CONFIRMADA
    assert (reserva.total, reserva.saldo, reserva.notas) == (150000, 100000, "Llega tarde")


@pytest.mark.parametrize("entrada, salida, personas, pagado, mensaje", [
    (dia(-1), dia(2), 2, 0, "anterior a hoy"),
    (dia(3), dia(3), 2, 0, "posterior a la entrada"),
    (dia(1), dia(2), 3, 0, "es para 2 personas"),
    (dia(1), dia(2), 2, 60000, "no puede superar el total"),
    (dia(1), dia(40), 2, 0, "hasta 30 noches"),
])
def test_crear_reserva_rechaza_datos_invalidos(habitacion, entrada, salida, personas, pagado, mensaje):
    with pytest.raises(ErrorDeNegocio, match=mensaje):
        crear_reserva(habitacion, huesped_nuevo(), entrada, salida, personas, HOY, pagado=pagado)


def test_crear_reserva_superpuesta_falla(habitacion, reservar):
    reservar(habitacion, dia(1), dia(4))
    with pytest.raises(ErrorDeNegocio, match="ya está reservada"):
        crear_reserva(habitacion, huesped_nuevo(), dia(3), dia(5), 1, HOY)


def test_checkin_en_el_mismo_paso(habitacion):
    reserva = crear_reserva(habitacion, huesped_nuevo(), HOY, dia(2), 2, HOY, checkin=True)
    assert reserva.estado == Reserva.EN_CURSO


def test_checkin_solo_si_entra_hoy_y_esta_limpia(habitacion):
    with pytest.raises(ErrorDeNegocio, match="todavía no se puede hacer el check-in"):
        crear_reserva(habitacion, huesped_nuevo(), dia(1), dia(2), 2, HOY, checkin=True)
    db.session.rollback()
    habitacion.estado_limpieza = Habitacion.SUCIA
    with pytest.raises(ErrorDeNegocio, match="está sucia"):
        crear_reserva(habitacion, huesped_nuevo(), HOY, dia(2), 2, HOY, checkin=True)


def test_buscar_huespedes_por_cada_palabra(app):
    db.session.add_all([
        Huesped(nombre="Lucía", apellido="Fernández", documento="30111222"),
        Huesped(nombre="Lucas", apellido="Pérez", email="lucas@example.com"),
    ])
    db.session.commit()
    assert [h.apellido for h in huespedes.buscar("luc")] == ["Fernández", "Pérez"]
    assert [h.apellido for h in huespedes.buscar("lu fern")] == ["Fernández"]
    assert [h.apellido for h in huespedes.buscar("30111")] == ["Fernández"]
    assert huespedes.buscar("l") == []  # muy corto
    assert huespedes.buscar("100%") == []  # el % no es un comodín


def test_huesped_nuevo_valida_los_datos(app):
    db.session.add(Huesped(nombre="Ana", apellido="Rossi", documento="30111222"))
    db.session.commit()
    with pytest.raises(ErrorDeNegocio, match="nombre y el apellido"):
        huespedes.nuevo_huesped("Ana", "  ")
    with pytest.raises(ErrorDeNegocio, match="Ana Rossi"):
        huespedes.nuevo_huesped("Otra", "Persona", documento="30 111 222")
    with pytest.raises(ErrorDeNegocio, match="no es válido"):
        huespedes.nuevo_huesped("Otra", "Persona", email="sin-arroba")
    nuevo = huespedes.nuevo_huesped("  Juan  Pablo ", "Gómez", pais="uy", email="JP@Example.com")
    assert (nuevo.nombre, nuevo.pais, nuevo.email) == ("Juan Pablo", "UY", "jp@example.com")


# --- Formulario y API ------------------------------------------------------------------------

def datos_formulario(habitacion, **cambios):
    hoy = date.today()
    datos = {
        "entrada": dia(1, hoy).isoformat(), "salida": dia(3, hoy).isoformat(), "personas": "2",
        "habitacion_id": str(habitacion.id), "nombre": "Lucía", "apellido": "Fernández",
        "documento": "", "pais": "AR", "email": "", "telefono": "", "pagado": "20000", "notas": "",
        "volver": "tape",
    }
    datos.update(cambios)
    return datos


def test_nueva_reserva_pide_login(anonimo):
    assert anonimo.get(URL).status_code == 302


def test_formulario_precompletado_desde_el_plano(cliente, habitacion):
    entrada = dia(2, date.today()).isoformat()
    html = cliente.get(f"{URL}?habitacion={habitacion.id}&entrada={entrada}&volver=plano").get_data(as_text=True)
    assert f'value="{habitacion.id}" required' in html
    assert 'data-numero="101"' in html and "checked" in html
    assert f'name="entrada" value="{entrada}"' in html
    assert 'name="volver" value="plano"' in html


def test_crear_reserva_con_huesped_nuevo(cliente, habitacion):
    respuesta = cliente.post(URL, data=datos_formulario(habitacion))
    reserva = db.session.scalar(db.select(Reserva))
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith(f"#reserva-{reserva.id}")
    assert reserva.huesped.nombre_completo == "Lucía Fernández"
    assert (reserva.total, reserva.pagado, reserva.huesped.pais) == (100000, 20000, "AR")


def test_crear_reserva_con_huesped_que_ya_vino(cliente, habitacion, reservar):
    reservar(habitacion, dia(-10, date.today()), dia(-8, date.today()), Reserva.FINALIZADA)
    habitue = db.session.scalar(db.select(Huesped))
    cliente.post(URL, data=datos_formulario(habitacion, huesped_id=str(habitue.id), nombre="", apellido=""))
    assert db.session.scalar(db.select(db.func.count(Huesped.id))) == 1
    assert len(habitue.reservas) == 2


def test_volver_al_plano_abre_la_habitacion(cliente, habitacion):
    respuesta = cliente.post(URL, data=datos_formulario(habitacion, volver="plano"))
    assert "/administracion/?fecha=" in respuesta.headers["Location"]
    assert respuesta.headers["Location"].endswith("#hab-101")


def test_error_no_guarda_y_conserva_lo_cargado(cliente, habitacion, reservar):
    reservar(habitacion, dia(0, date.today()), dia(5, date.today()))
    respuesta = cliente.post(URL, data=datos_formulario(habitacion, notas="Pidió cuna"))
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 422
    assert "ya está reservada" in html
    assert "Pidió cuna" in html and 'value="Fernández"' in html
    assert db.session.scalar(db.select(db.func.count(Reserva.id))) == 1


def test_api_disponibilidad(cliente, habitacion, simple, reservar):
    hoy = date.today()
    reservar(habitacion, dia(1, hoy), dia(3, hoy))
    datos = cliente.get(f"/administracion/api/disponibilidad?entrada={dia(2, hoy)}&salida={dia(4, hoy)}&personas=1").get_json()
    assert {h["id"]: h["estado"] for h in datos["habitaciones"]} == {habitacion.id: "ocupada", simple.id: "libre"}
    assert cliente.get(f"/administracion/api/disponibilidad?entrada={dia(4, hoy)}&salida={dia(2, hoy)}").status_code == 400


def test_api_buscar_huespedes(cliente, habitacion, reservar):
    reservar(habitacion, dia(1, date.today()), dia(2, date.today()))
    datos = cliente.get("/administracion/api/huespedes?q=ross").get_json()
    assert datos["huespedes"][0]["nombre"] == "Ana Rossi"
    assert datos["huespedes"][0]["estadias"] == 1


def test_botones_de_nueva_reserva_habilitados(cliente, habitacion):
    assert f'href="{URL}' in cliente.get("/administracion/").get_data(as_text=True)
    assert f'href="{URL}"' in cliente.get("/administracion/reservas/").get_data(as_text=True)
