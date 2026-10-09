import io
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.extensions import db
from app.models import ConfiguracionHotel, Habitacion, TipoHabitacion, Usuario
from app.services.configuracion import eliminar_usuario
from app.services.errores import ErrorDeNegocio

URL = "/administracion/configuracion"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 64


@pytest.fixture
def admin(app):
    admin = Usuario(nombre="Ana Admin", email="ana@hotel.test", rol=Usuario.ADMIN)
    admin.set_password("clave-admin")
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def cliente_admin(app, admin):
    cliente = app.test_client()
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = admin.id
    return cliente


@pytest.fixture
def doble(app):
    tipo = TipoHabitacion(nombre="Doble", capacidad=2, tarifa_base=50000, slug="doble")
    db.session.add(tipo)
    db.session.commit()
    return tipo


def subidas(app):
    return sorted(p.name for p in (Path(app.instance_path) / "uploads").iterdir())


def datos_tipo(**cambios):
    datos = {"nombre": "Suite Lago", "capacidad": "4", "tarifa": "90000", "metros": "32",
             "descripcion": "Con vista al lago.", "comodidades": "Cama king\n\n  Bañera  \n"}
    datos.update(cambios)
    return datos


# --- Acceso -------------------------------------------------------------------------

def test_recepcion_no_entra_a_configuracion(cliente):
    respuesta = cliente.get(f"{URL}/")
    assert respuesta.status_code == 302
    assert respuesta.location == "/administracion/"
    assert "Configuración" not in cliente.get("/administracion/").get_data(as_text=True)


def test_administracion_ve_todas_las_pantallas(cliente_admin, doble):
    for ruta in ("/", "/habitaciones", "/tipos/nuevo", f"/tipos/{doble.id}", "/usuarios"):
        assert cliente_admin.get(URL + ruta).status_code == 200, ruta


# --- Hotel -----------------------------------------------------------------------------

def test_guardar_datos_del_hotel(cliente_admin, app):
    respuesta = cliente_admin.post(f"{URL}/", data={
        "nombre": "Hotel Lenga", "eslogan": "Bosque y lago", "ciudad": "El Bolsón", "moneda": "$",
        "hora_checkin": "15:00", "hora_checkout": "11:00", "color_acento": "#7f1d1d",
        "logo": (io.BytesIO(PNG), "logo.png"),
    }, content_type="multipart/form-data")
    assert respuesta.status_code == 302
    config = ConfiguracionHotel.actual()
    assert (config.nombre, config.color_acento, config.hora_checkin) == ("Hotel Lenga", "#7F1D1D", "15:00")
    assert config.logo in subidas(app)


def test_color_invalido_no_guarda(cliente_admin):
    respuesta = cliente_admin.post(f"{URL}/", data={
        "nombre": "Hotel Lenga", "hora_checkin": "15:00", "hora_checkout": "11:00",
        "color_acento": "red; background: url(x)",
    })
    assert respuesta.status_code == 422
    assert db.session.scalar(db.select(ConfiguracionHotel)) is None


# --- Tipos de habitación ----------------------------------------------------------------

def test_crear_tipo_con_foto_y_modelo(cliente_admin, app):
    datos = datos_tipo(imagen=(io.BytesIO(PNG), "suite.png"), modelo=(io.BytesIO(GLB), "suite.glb"))
    respuesta = cliente_admin.post(f"{URL}/tipos/nuevo", data=datos, content_type="multipart/form-data")
    assert respuesta.status_code == 302

    tipo = db.session.scalar(db.select(TipoHabitacion))
    assert tipo.slug == "suite-lago"
    assert tipo.lista_comodidades == ["Cama king", "Bañera"]
    assert tipo.imagen.endswith(".png") and tipo.modelo.endswith(".glb")
    assert subidas(app) == sorted([tipo.imagen, tipo.modelo])


def test_archivo_disfrazado_se_rechaza_y_no_queda_nada(cliente_admin, app):
    datos = datos_tipo(imagen=(io.BytesIO(PNG), "suite.png"), modelo=(io.BytesIO(b"no soy un glb"), "suite.glb"))
    respuesta = cliente_admin.post(f"{URL}/tipos/nuevo", data=datos, content_type="multipart/form-data")
    assert respuesta.status_code == 422
    assert "no es un modelo 3D" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(TipoHabitacion)) is None
    assert subidas(app) == []  # la foto que sí era válida también se borró


def test_quitar_la_foto_de_un_tipo(cliente_admin, app):
    cliente_admin.post(f"{URL}/tipos/nuevo", data=datos_tipo(imagen=(io.BytesIO(PNG), "suite.png")),
                       content_type="multipart/form-data")
    tipo = db.session.scalar(db.select(TipoHabitacion))
    cliente_admin.post(f"{URL}/tipos/{tipo.id}", data=datos_tipo(quitar_imagen="on"),
                       content_type="multipart/form-data")
    db.session.refresh(tipo)
    assert tipo.imagen is None
    assert subidas(app) == []


def test_nombre_de_tipo_repetido(cliente_admin, doble):
    respuesta = cliente_admin.post(f"{URL}/tipos/nuevo", data=datos_tipo(nombre="doble"))
    assert respuesta.status_code == 422
    assert "Ya existe un tipo" in respuesta.get_data(as_text=True)


def test_no_se_borra_un_tipo_con_habitaciones(cliente_admin, doble):
    db.session.add(Habitacion(numero="101", piso=1, tipo=doble))
    db.session.commit()
    cliente_admin.post(f"{URL}/tipos/{doble.id}/eliminar")
    assert db.session.get(TipoHabitacion, doble.id) is not None


# --- Pisos y habitaciones -------------------------------------------------------------------

def numeros():
    return [h.numero for h in db.session.scalars(db.select(Habitacion).order_by(Habitacion.numero))]


def test_agregar_habitaciones_numera_solo(cliente_admin, doble):
    cliente_admin.post(f"{URL}/habitaciones/agregar", data={"piso": "3", "cantidad": "3", "tipo_id": doble.id})
    cliente_admin.post(f"{URL}/habitaciones/agregar", data={"piso": "3", "cantidad": "2", "tipo_id": doble.id})
    assert numeros() == ["301", "302", "303", "304", "305"]


def test_no_se_duplican_numeros(cliente_admin, doble):
    cliente_admin.post(f"{URL}/habitaciones/agregar", data={"piso": "1", "cantidad": "2", "tipo_id": doble.id})
    cliente_admin.post(f"{URL}/habitaciones/agregar",
                       data={"piso": "1", "cantidad": "3", "tipo_id": doble.id, "desde": "2"})
    assert numeros() == ["101", "102"]


def test_no_se_borra_una_habitacion_con_reservas(cliente_admin, habitacion, reservar):
    reservar(habitacion, date.today(), date.today() + timedelta(days=2))
    cliente_admin.post(f"{URL}/habitaciones/{habitacion.id}/eliminar")
    assert db.session.get(Habitacion, habitacion.id) is not None


def test_borrar_una_habitacion_sin_reservas(cliente_admin, habitacion):
    cliente_admin.post(f"{URL}/habitaciones/{habitacion.id}/eliminar")
    assert db.session.get(Habitacion, habitacion.id) is None


def test_cambiar_tipo_respeta_la_capacidad(cliente_admin, habitacion, reservar):
    simple = TipoHabitacion(nombre="Simple", capacidad=1, tarifa_base=30000, slug="simple")
    db.session.add(simple)
    reserva = reservar(habitacion, date.today() + timedelta(days=1), date.today() + timedelta(days=3))
    reserva.personas = 2
    db.session.commit()
    cliente_admin.post(f"{URL}/habitaciones/{habitacion.id}/tipo", data={"tipo_id": simple.id})
    db.session.refresh(habitacion)
    assert habitacion.tipo.nombre == "Doble"


# --- Usuarios ----------------------------------------------------------------------------------

def test_crear_usuario(cliente_admin):
    respuesta = cliente_admin.post(f"{URL}/usuarios", data={
        "nombre": "Martín Gómez", "email": "Martin@Hotel.test", "rol": "recepcion", "password": "secreta",
    })
    assert respuesta.status_code == 302
    nuevo = db.session.scalar(db.select(Usuario).where(Usuario.email == "martin@hotel.test"))
    assert nuevo.rol == Usuario.RECEPCION and nuevo.check_password("secreta")


def test_email_repetido(cliente_admin, admin):
    respuesta = cliente_admin.post(f"{URL}/usuarios", data={
        "nombre": "Otra Ana", "email": admin.email, "rol": "recepcion", "password": "secreta",
    })
    assert respuesta.status_code == 422


def test_no_podes_borrarte_a_vos_mismo(cliente_admin, admin):
    cliente_admin.post(f"{URL}/usuarios/{admin.id}/eliminar")
    assert db.session.get(Usuario, admin.id) is not None


def test_queda_al_menos_un_admin(admin, usuario):
    with pytest.raises(ErrorDeNegocio, match="al menos un usuario de administración"):
        eliminar_usuario(admin, actual=usuario)
