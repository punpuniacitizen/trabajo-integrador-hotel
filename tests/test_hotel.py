import pytest

from app.extensions import db
from app.models import ConfiguracionHotel, Habitacion, TipoHabitacion, Usuario
from app.services.errores import ErrorDeNegocio
from app.services.hotel import (
    icono_servicio,
    normalizar_instagram,
    normalizar_whatsapp,
    parsear_coordenadas,
)

URL = "/administracion/configuracion/"


@pytest.mark.parametrize("texto, esperado", [
    ("-41.1262, -71.3476", (-41.1262, -71.3476)),
    ("-41.1262,-71.3476", (-41.1262, -71.3476)),
    ("https://www.google.com/maps/@-41.1262,-71.3476,17z", (-41.1262, -71.3476)),
    ("https://www.google.com/maps/place/Hotel/@-41.2,-71.4,15z/data=!3d-41.1262!4d-71.3476", (-41.1262, -71.3476)),
    ("", None),
])
def test_parsear_coordenadas(texto, esperado):
    assert parsear_coordenadas(texto) == esperado


@pytest.mark.parametrize("texto", ["cerca del lago", "95.0, 10.0"])
def test_coordenadas_invalidas(texto):
    with pytest.raises(ErrorDeNegocio):
        parsear_coordenadas(texto)


def test_normalizar_contacto():
    assert normalizar_whatsapp("+54 9 294 400-0000") == "5492944000000"
    assert normalizar_whatsapp("") is None
    assert normalizar_instagram("@hotel.mirador") == "hotel.mirador"
    assert normalizar_instagram("https://www.instagram.com/hotel.mirador/?hl=es") == "hotel.mirador"
    with pytest.raises(ErrorDeNegocio):
        normalizar_whatsapp("123")


def test_icono_segun_el_servicio():
    assert icono_servicio("Desayuno casero incluido") == "taza"
    assert icono_servicio("Wi-Fi en todo el hotel") == "wifi"
    assert icono_servicio("Algo raro") == "check"


def test_links_del_hotel():
    config = ConfiguracionHotel(nombre="H", direccion="Av. Bustillo 4200", ciudad="Bariloche",
                                telefono="+54 294 400-0000", whatsapp="5492944000000")
    assert "q=Av.%20Bustillo%204200%2C%20Bariloche" in config.url_mapa
    assert config.url_telefono == "tel:+542944000000"
    assert config.url_whatsapp == "https://wa.me/5492944000000"
    config.latitud, config.longitud = -41.1, -71.3
    assert "q=-41.1%2C-71.3" in config.url_mapa  # con coordenadas, gana el punto exacto


# --- Configuración ---------------------------------------------------------------------

@pytest.fixture
def cliente_admin(app):
    admin = Usuario(nombre="Ana Admin", email="ana@hotel.test", rol=Usuario.ADMIN)
    admin.set_password("clave-admin")
    db.session.add(admin)
    db.session.commit()
    cliente = app.test_client()
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = admin.id
    return cliente


def datos_hotel(**cambios):
    datos = {
        "nombre": "Hotel Lenga", "ciudad": "El Bolsón", "hora_checkin": "14:00", "hora_checkout": "10:00",
        "color_acento": "#1F6F5C", "presentacion": "Primer párrafo.\n\nSegundo párrafo.",
        "servicios": "Desayuno\n\n Wi-Fi \n", "informacion": "No se fuma.",
        "direccion": "Calle 1", "coordenadas": "-41.96, -71.53",
        "telefono": "+54 294 400-0000", "email": "Hola@Lenga.Example",
        "whatsapp": "+54 9 294 400-0000", "instagram": "@hotel.lenga",
    }
    datos.update(cambios)
    return datos


def test_guardar_ubicacion_y_contacto(cliente_admin):
    assert cliente_admin.post(URL, data=datos_hotel()).status_code == 302
    config = ConfiguracionHotel.actual()
    assert (config.latitud, config.longitud) == (-41.96, -71.53)
    assert config.servicios == "Desayuno\nWi-Fi"
    assert config.parrafos_presentacion == ["Primer párrafo.", "Segundo párrafo."]
    assert (config.email, config.whatsapp, config.instagram) == ("hola@lenga.example", "5492944000000", "hotel.lenga")


def test_coordenadas_que_no_se_entienden_no_guardan(cliente_admin):
    respuesta = cliente_admin.post(URL, data=datos_hotel(coordenadas="por ahí"))
    assert respuesta.status_code == 422
    assert "No se entienden las coordenadas" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(ConfiguracionHotel)) is None


# --- Página principal --------------------------------------------------------------------

@pytest.fixture
def tipos(app):
    doble = TipoHabitacion(nombre="Doble", capacidad=2, tarifa_base=50000, slug="doble")
    suite = TipoHabitacion(nombre="Suite", capacidad=4, tarifa_base=90000, slug="suite")
    db.session.add_all([Habitacion(numero="101", piso=1, tipo=doble), Habitacion(numero="102", piso=1, tipo=suite)])
    db.session.commit()
    return doble, suite


def test_inicio_con_mapa_servicios_y_contacto(cliente_admin, anonimo, tipos):
    cliente_admin.post(URL, data=datos_hotel())
    html = anonimo.get("/").get_data(as_text=True)
    assert 'src="https://maps.google.com/maps?q=-41.96%2C-71.53' in html
    assert "#i-taza" in html and "#i-wifi" in html  # íconos elegidos según el servicio
    assert "https://wa.me/5492944000000" in html
    assert "Segundo párrafo." in html
    assert 'action="/reservar"' in html  # buscador de fechas de la portada


def test_inicio_sin_datos_opcionales(anonimo, tipos):
    html = anonimo.get("/").get_data(as_text=True)
    assert "maps.google.com" not in html
    assert 'id="servicios"' not in html


def test_buscador_para_4_personas_propone_un_tipo_donde_entren(anonimo, tipos):
    html = anonimo.get("/reservar?personas=4").get_data(as_text=True)
    assert 'value="suite" checked' in html
