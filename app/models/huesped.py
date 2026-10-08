from app.extensions import db


class Huesped(db.Model):
    __tablename__ = "huespedes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    documento = db.Column(db.String(20))
    email = db.Column(db.String(120))
    telefono = db.Column(db.String(40))
    pais = db.Column(db.String(2))  # código ISO de dos letras, por ejemplo "AR"

    reservas = db.relationship("Reserva", back_populates="huesped")

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
