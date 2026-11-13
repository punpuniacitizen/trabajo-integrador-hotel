"""Datos del hotel que se cargan en Configuración: color, ubicación, contacto e íconos de servicios."""
import re

from app.services.errores import ErrorDeNegocio

# --- Color de acento ----------------------------------------------------------------------

TINTA = "#18181B"  # color por defecto y texto oscuro
BLANCO = "#FFFFFF"
_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def es_color_valido(color):
    return bool(color and _HEX.fullmatch(color))


def texto_sobre(color):
    """El color del texto que va encima del acento (botones, avatares): blanco o casi negro.

    Usa el brillo percibido del color (el verde pesa más que el rojo y el azul).
    El mismo cálculo está en configuracion.js para la vista previa.
    """
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    brillo = 0.299 * r + 0.587 * g + 0.114 * b
    return TINTA if brillo > 150 else BLANCO


# --- Ubicación y contacto ---------------------------------------------------------------

# "-41.1262, -71.3476", o un link de Google Maps que tenga "@-41.12,-71.34"
_PAR = re.compile(r"(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_USUARIO_INSTAGRAM = re.compile(r"[A-Za-z0-9._]{1,30}")


def parsear_coordenadas(texto):
    """Devuelve (latitud, longitud) o None si el texto está vacío. Error si no se entiende."""
    texto = (texto or "").strip()
    if not texto:
        return None
    coincidencia = _PAR.search(texto)
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
        raise ErrorDeNegocio(f"El email {texto} no es válido.")
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


# --- Íconos de los servicios ----------------------------------------------------------------

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
