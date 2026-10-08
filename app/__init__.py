import os

from flask import Flask

from config import Config


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)

    # Ruta provisoria hasta registrar los blueprints de app/routes/
    @app.route("/")
    def index():
        return "Sistema de gestión hotelera: en construcción"

    return app
