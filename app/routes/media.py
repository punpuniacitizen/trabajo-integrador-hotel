import os

from flask import Blueprint, current_app, send_from_directory

bp = Blueprint("media", __name__, url_prefix="/media")


@bp.get("/<path:nombre>")
def archivo(nombre):
    """Archivos que sube el hotel desde Configuración, guardados en instance/uploads/."""
    respuesta = send_from_directory(os.path.join(current_app.instance_path, "uploads"), nombre)
    # Un SVG abierto directo podría traer scripts: se sirven sin poder ejecutar nada
    respuesta.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    return respuesta
