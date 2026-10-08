# Trabajo Integrador: Sistema de Gestión Hotelera

Aplicación web de gestión interna para un hotel ficticio, hecha con Flask, HTML, CSS y JavaScript.

## Stack

- **Backend:** Python 3.12 + Flask (app factory + blueprints)
- **Base de datos:** SQLite con Flask-SQLAlchemy
- **Frontend:** plantillas Jinja2, CSS propio y JavaScript sin frameworks

## Estructura

```
app/
  models/       modelos de la base de datos
  routes/       blueprints (una sección del sistema por archivo)
  services/     integración con APIs externas
  templates/    plantillas HTML (components/ para piezas reutilizables)
  static/       css/, js/, img/ y brand/ (logos y favicon)
design/         identidad visual y pantallas de Google Stitch
docs/           documentación del trabajo
scripts/        utilidades (por ejemplo, cargar datos de prueba)
tests/          pruebas
config.py       configuración
run.py          punto de entrada
```

## Cómo correrlo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Después abrir http://127.0.0.1:5000
