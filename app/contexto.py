"""Variables que tienen todas las plantillas: el hotel, su color y la fecha."""
from datetime import datetime

from flask import g

from app.models import ConfiguracionHotel
from app.services.tema import TINTA, es_color_valido, texto_sobre


def turno(hora):
    if 6 <= hora < 14:
        return "Mañana"
    if 14 <= hora < 22:
        return "Tarde"
    return "Noche"


def registrar(app):
    @app.before_request
    def cargar_hotel():
        g.hotel = ConfiguracionHotel.actual()

    @app.context_processor
    def variables_globales():
        hotel = g.get("hotel") or ConfiguracionHotel.actual()
        # El acento va dentro de un <style>: solo se acepta un #RRGGBB válido.
        acento = hotel.color_acento if es_color_valido(hotel.color_acento) else TINTA
        ahora = datetime.now()
        return {
            "hotel": hotel,
            "acento": acento,
            "acento_texto": texto_sobre(acento),
            "hoy": ahora.date(),
            "turno": turno(ahora.hour),
        }
