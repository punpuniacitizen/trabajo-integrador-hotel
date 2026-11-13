"""Variables que tienen todas las plantillas: el hotel, su color, el usuario y la fecha."""
from datetime import datetime

from flask import g, session

from app.extensions import db
from app.models import ConfiguracionHotel, Usuario
from app.services.hotel import TINTA, es_color_valido, texto_sobre


def turno(hora):
    if 6 <= hora < 14:
        return "Mañana"
    if 14 <= hora < 22:
        return "Tarde"
    return "Noche"


def registrar(app):
    @app.before_request
    def cargar_hotel_y_usuario():
        g.hotel = ConfiguracionHotel.actual()
        usuario_id = session.get("usuario_id")
        g.usuario = db.session.get(Usuario, usuario_id) if usuario_id else None

    @app.context_processor
    def variables_globales():
        hotel = g.get("hotel") or ConfiguracionHotel.actual()
        # El acento va dentro de un <style>: solo se acepta un #RRGGBB válido.
        acento = hotel.color_acento if es_color_valido(hotel.color_acento) else TINTA
        ahora = datetime.now()
        return {
            "hotel": hotel,
            "usuario": g.get("usuario"),
            "acento": acento,
            "acento_texto": texto_sobre(acento),
            "hoy": ahora.date(),
            "turno": turno(ahora.hour),
        }
