from datetime import datetime

from app.extensions import db


class Reserva(db.Model):
    __tablename__ = "reservas"

    CONFIRMADA = "confirmada"  # todavía no llegó
    EN_CURSO = "en_curso"  # hizo el check-in
    FINALIZADA = "finalizada"  # hizo el check-out
    CANCELADA = "cancelada"
    NO_SHOW = "no_show"  # tenía que llegar y no se presentó

    INACTIVAS = (CANCELADA, NO_SHOW)  # no ocupan la habitación

    id = db.Column(db.Integer, primary_key=True)
    huesped_id = db.Column(db.Integer, db.ForeignKey("huespedes.id"), nullable=False)
    habitacion_id = db.Column(db.Integer, db.ForeignKey("habitaciones.id"), nullable=False)
    entrada = db.Column(db.Date, nullable=False)
    salida = db.Column(db.Date, nullable=False)  # día del check-out: esa noche ya no se ocupa
    personas = db.Column(db.Integer, nullable=False, default=1)
    estado = db.Column(db.String(12), nullable=False, default=CONFIRMADA)
    total = db.Column(db.Integer, nullable=False, default=0)
    pagado = db.Column(db.Integer, nullable=False, default=0)
    notas = db.Column(db.Text)
    token = db.Column(db.String(24), unique=True, index=True)  # link de confirmación de las reservas web
    creada = db.Column(db.DateTime, nullable=False, default=datetime.now)

    huesped = db.relationship("Huesped", back_populates="reservas")
    habitacion = db.relationship("Habitacion", back_populates="reservas")

    @property
    def noches(self):
        return (self.salida - self.entrada).days

    @property
    def saldo(self):
        return self.total - self.pagado

    @property
    def codigo(self):
        return f"#{self.id:04d}"
