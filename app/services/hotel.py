"""Normalización de los datos del hotel que se cargan en Configuración: ubicación y contacto."""
import re

from app.services.errores import ErrorDeNegocio

# "-41.1262, -71.3476", o un link de Google Maps con "@-41.12,-71.34" o "q=-41.12,-71.34"
_PAR = re.compile(r"(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)")
# Los links largos de Google Maps marcan el lugar con "!3d<latitud>!4d<longitud>"
_PIN = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_USUARIO_INSTAGRAM = re.compile(r"[A-Za-z0-9._]{1,30}")


def parsear_coordenadas(texto):
    """Devuelve (latitud, longitud) o None si el texto está vacío. Error si no se entiende."""
    texto = (texto or "").strip()
    if not texto:
        return None
    coincidencia = _PIN.search(texto) or _PAR.search(texto)
    if coincidencia:
        latitud, longitud = float(coincidencia.group(1)), float(coincidencia.group(2))
        if -90 <= latitud <= 90 and -180 <= longitud <= 180:
            return round(latitud, 6), round(longitud, 6)
    raise ErrorDeNegocio(
        "No se entienden las coordenadas. Escribilas como -41.1262, -71.3476 o pegá un link de Google Maps."
    )


def normalizar_email(texto):
    texto = (texto or "").strip().lower()
    if texto and not _EMAIL.fullmatch(texto):
        raise ErrorDeNegocio("El email de contacto no es válido.")
    return texto or None


def normalizar_whatsapp(texto):
    """"+54 9 294 400-0000" -> "5492944000000" (lo que pide wa.me)."""
    digitos = re.sub(r"\D", "", texto or "")
    if texto and texto.strip() and not 8 <= len(digitos) <= 15:
        raise ErrorDeNegocio("El WhatsApp tiene que ser un número con código de país, por ejemplo +54 9 294 400-0000.")
    return digitos or None


def normalizar_instagram(texto):
    """"@hotel", "hotel" o "https://instagram.com/hotel/" -> "hotel"."""
    texto = (texto or "").strip()
    if not texto:
        return None
    usuario = re.sub(r"^(https?://)?(www\.)?instagram\.com/", "", texto).strip("/@ ")
    usuario = usuario.split("/")[0].split("?")[0]
    if not _USUARIO_INSTAGRAM.fullmatch(usuario):
        raise ErrorDeNegocio("El usuario de Instagram no es válido.")
    return usuario


# Ícono de cada servicio según lo que dice el texto (el primero que coincide)
_ICONOS_SERVICIO = [
    (("desayun", "merienda", "café"), "taza"),
    (("wi-fi", "wifi", "internet"), "wifi"),
    (("estacionamiento", "cochera", "parking", "traslado", "transfer"), "auto"),
    (("pileta", "piscina", "jacuzzi"), "pileta"),
    (("spa", "sauna", "masaje"), "hoja"),
    (("gimnasio", "gym"), "pesa"),
    (("restaurante", "comida", "cena", "almuerzo", "bar"), "cubiertos"),
    (("mascota", "perro", "pet"), "pata"),
    (("calefacc", "aire acondicionado", "climatiz"), "termometro"),
    (("24", "recepción", "recepcion"), "reloj"),
    (("lago", "vista", "montaña", "playa"), "mapa"),
]


def icono_servicio(texto):
    texto = texto.lower()
    for claves, icono in _ICONOS_SERVICIO:
        if any(clave in texto for clave in claves):
            return icono
    return "check"
