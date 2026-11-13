import re
from urllib.parse import quote

from app.extensions import db


def _lineas(texto):
    return [linea.strip() for linea in (texto or "").splitlines() if linea.strip()]


class ConfiguracionHotel(db.Model):
    """Datos del hotel que instaló el sistema. Hay una sola fila."""

    __tablename__ = "configuracion_hotel"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    logo = db.Column(db.String(255))  # nombre del archivo dentro de instance/uploads/
    color_acento = db.Column(db.String(7), nullable=False, default="#18181B")
    ciudad = db.Column(db.String(120))
    eslogan = db.Column(db.String(160))  # título de la portada del sitio público
    portada = db.Column(db.String(255))  # imagen de la portada del sitio público (en instance/uploads/)
    moneda = db.Column(db.String(8), nullable=False, default="$")
    hora_checkin = db.Column(db.String(5), nullable=False, default="14:00")
    hora_checkout = db.Column(db.String(5), nullable=False, default="10:00")

    # Sitio público: textos (una entrada por línea en servicios e información útil)
    presentacion = db.Column(db.Text)  # párrafos separados por una línea en blanco
    servicios = db.Column(db.Text)
    informacion = db.Column(db.Text)

    # Ubicación: si hay coordenadas, el mapa usa esas; si no, busca la dirección
    direccion = db.Column(db.String(200))
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)

    # Contacto
    telefono = db.Column(db.String(40))
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(30))  # solo dígitos, con código de país (5492944000000)
    instagram = db.Column(db.String(60))  # usuario, sin @

    @classmethod
    def actual(cls):
        """La configuración guardada o, si todavía no hay, una con valores por defecto (sin guardar)."""
        config = db.session.scalar(db.select(cls).limit(1))
        # Los default de las columnas recién se aplican al guardar: por eso se repiten acá
        return config or cls(nombre="Mi hotel", color_acento="#18181B", moneda="$",
                             hora_checkin="14:00", hora_checkout="10:00")

    # --- Textos del sitio --------------------------------------------------------

    @property
    def parrafos_presentacion(self):
        return [" ".join(p.split()) for p in re.split(r"\n\s*\n", self.presentacion or "") if p.strip()]

    @property
    def lista_servicios(self):
        return _lineas(self.servicios)

    @property
    def lista_informacion(self):
        return _lineas(self.informacion)

    # --- Mapa (Google Maps, sin clave de API) --------------------------------------

    @property
    def tiene_coordenadas(self):
        return self.latitud is not None and self.longitud is not None

    @property
    def consulta_mapa(self):
        """Lo que se busca en el mapa: las coordenadas o "dirección, ciudad"."""
        if self.tiene_coordenadas:
            return f"{self.latitud},{self.longitud}"
        if self.direccion:
            return ", ".join(p for p in (self.direccion, self.ciudad) if p)
        return None

    @property
    def url_mapa(self):
        if not self.consulta_mapa:
            return None
        return f"https://maps.google.com/maps?q={quote(self.consulta_mapa)}&z=15&output=embed"

    @property
    def url_como_llegar(self):
        if not self.consulta_mapa:
            return None
        return f"https://www.google.com/maps/dir/?api=1&destination={quote(self.consulta_mapa)}"

    # --- Contacto -------------------------------------------------------------------

    @property
    def url_telefono(self):
        return "tel:" + re.sub(r"[^\d+]", "", self.telefono) if self.telefono else None

    @property
    def url_whatsapp(self):
        return f"https://wa.me/{self.whatsapp}" if self.whatsapp else None

    @property
    def url_instagram(self):
        return f"https://www.instagram.com/{self.instagram}/" if self.instagram else None

    @property
    def tiene_contacto(self):
        return any((self.telefono, self.email, self.whatsapp, self.instagram))
