import pytest

from app import create_app
from app.extensions import db
from app.models import Habitacion, Huesped, Reserva, TipoHabitacion


class ConfigPruebas:
    TESTING = True
    SECRET_KEY = "pruebas"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # base en memoria
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture
def app():
    app = create_app(ConfigPruebas)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente(app):
    return app.test_client()


@pytest.fixture
def habitacion(app):
    tipo = TipoHabitacion(nombre="Doble", capacidad=2, tarifa_base=50000)
    habitacion = Habitacion(numero="101", piso=1, tipo=tipo)
    db.session.add(habitacion)
    db.session.commit()
    return habitacion


@pytest.fixture
def reservar(app):
    """reservar(habitacion, entrada, salida, estado) crea y guarda una reserva."""
    huesped = Huesped(nombre="Ana", apellido="Rossi", documento="30111222")
    db.session.add(huesped)

    def crear(habitacion, entrada, salida, estado=Reserva.CONFIRMADA):
        reserva = Reserva(huesped=huesped, habitacion=habitacion, entrada=entrada, salida=salida, estado=estado)
        db.session.add(reserva)
        db.session.commit()
        return reserva

    return crear
