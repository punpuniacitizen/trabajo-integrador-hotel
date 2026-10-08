import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-solo-para-desarrollo")
    # Ruta relativa a la carpeta instance/ (SQLite por defecto)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///hotel.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
