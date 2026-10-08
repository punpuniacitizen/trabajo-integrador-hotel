from app.extensions import db


class TipoHabitacion(db.Model):
    __tablename__ = "tipos_habitacion"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    capacidad = db.Column(db.Integer, nullable=False)
    tarifa_base = db.Column(db.Integer, nullable=False)  # por noche, en pesos enteros

    habitaciones = db.relationship("Habitacion", back_populates="tipo")


class Habitacion(db.Model):
    """Habitación física. Solo guarda su estado físico: la ocupación sale de las reservas."""

    __tablename__ = "habitaciones"

    LIMPIA = "limpia"
    SUCIA = "sucia"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), nullable=False, unique=True)
    piso = db.Column(db.Integer, nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey("tipos_habitacion.id"), nullable=False)
    estado_limpieza = db.Column(db.String(10), nullable=False, default=LIMPIA)
    fuera_de_servicio = db.Column(db.Boolean, nullable=False, default=False)
    nota_mantenimiento = db.Column(db.String(200))

    tipo = db.relationship("TipoHabitacion", back_populates="habitaciones")
    reservas = db.relationship("Reserva", back_populates="habitacion")
