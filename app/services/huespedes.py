"""Huéspedes: búsqueda para la recepción y alta de un huésped nuevo al cargar una reserva."""
from sqlalchemy import or_

from app.extensions import db
from app.models import Huesped
from app.services.errores import ErrorDeNegocio
from app.services.hotel import normalizar_email

# Los países que más se ven en un hotel argentino (código ISO de dos letras)
PAISES = [
    ("AR", "Argentina"), ("UY", "Uruguay"), ("CL", "Chile"), ("BR", "Brasil"), ("PY", "Paraguay"),
    ("BO", "Bolivia"), ("PE", "Perú"), ("CO", "Colombia"), ("MX", "México"), ("US", "Estados Unidos"),
    ("CA", "Canadá"), ("ES", "España"), ("IT", "Italia"), ("FR", "Francia"), ("DE", "Alemania"),
    ("GB", "Reino Unido"), ("IL", "Israel"), ("AU", "Australia"),
]
NOMBRES_PAISES = dict(PAISES)
MINIMO_BUSQUEDA = 2


def buscar(texto, limite=8):
    """Huéspedes cuyo nombre, apellido, documento o email contiene cada palabra buscada."""
    palabras = (texto or "").split()
    if len("".join(palabras)) < MINIMO_BUSQUEDA:
        return []
    consulta = db.select(Huesped)
    for palabra in palabras:
        consulta = consulta.where(or_(
            Huesped.nombre.icontains(palabra, autoescape=True),
            Huesped.apellido.icontains(palabra, autoescape=True),
            Huesped.documento.icontains(palabra, autoescape=True),
            Huesped.email.icontains(palabra, autoescape=True),
        ))
    return db.session.scalars(consulta.order_by(Huesped.apellido, Huesped.nombre).limit(limite)).all()


def _limpio(texto, largo):
    return " ".join((texto or "").split())[:largo]


def nuevo_huesped(nombre, apellido, documento=None, email=None, telefono=None, pais=None):
    """Arma un huésped nuevo con los datos del formulario (la ruta lo guarda junto con la reserva)."""
    nombre, apellido = _limpio(nombre, 80), _limpio(apellido, 80)
    if not nombre or not apellido:
        raise ErrorDeNegocio("Completá el nombre y el apellido del huésped, o buscá uno que ya vino.")

    documento = "".join((documento or "").split())[:20] or None
    if documento:
        repetido = db.session.scalar(db.select(Huesped).where(Huesped.documento == documento).limit(1))
        if repetido:
            raise ErrorDeNegocio(
                f"Ya hay un huésped con el documento {documento}: {repetido.nombre_completo}. Buscalo y elegilo."
            )

    email = normalizar_email(email)

    pais = (pais or "").upper() or None
    if pais and pais not in NOMBRES_PAISES:
        raise ErrorDeNegocio("Elegí el país de la lista.")

    return Huesped(nombre=nombre, apellido=apellido, documento=documento, email=email,
                   telefono=_limpio(telefono, 40) or None, pais=pais)
