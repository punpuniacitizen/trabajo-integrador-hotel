import os

from flask import Blueprint, current_app, send_from_directory

bp = Blueprint("media", __name__, url_prefix="/media")


@bp.get("/<path:nombre>")
def archivo(nombre):
    """Archivos que sube el hotel (por ahora, su logo), guardados en instance/uploads/."""
    return send_from_directory(os.path.join(current_app.instance_path, "uploads"), nombre)
