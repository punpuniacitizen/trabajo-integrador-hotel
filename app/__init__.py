import os

from flask import Flask

from app.extensions import db
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(os.path.join(app.instance_path, "uploads"), exist_ok=True)

    db.init_app(app)

    from app import contexto, filtros
    from app.comandos import crear_usuario_command
    from app.demo import demo_command
    from app.routes import api, auth, configuracion, media, plano, reservas, sitio

    contexto.registrar(app)
    filtros.registrar(app)
    app.register_blueprint(sitio.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(plano.bp)
    app.register_blueprint(reservas.bp)
    app.register_blueprint(configuracion.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(media.bp)
    app.cli.add_command(demo_command)
    app.cli.add_command(crear_usuario_command)

    with app.app_context():
        db.create_all()

    return app
