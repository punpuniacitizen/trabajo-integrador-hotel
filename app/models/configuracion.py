from app.extensions import db


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
    setup_completo = db.Column(db.Boolean, nullable=False, default=False)

    @classmethod
    def actual(cls):
        """La configuración guardada o, si todavía no hay, una con valores por defecto (sin guardar)."""
        config = db.session.scalar(db.select(cls).limit(1))
        if config:
            return config
        return cls(
            nombre="Mi hotel",
            color_acento="#18181B",
            moneda="$",
            hora_checkin="14:00",
            hora_checkout="10:00",
            setup_completo=False,
        )
