# Conserje: sistema de gestión hotelera

Trabajo integrador. **Conserje** es un software de gestión interna pensado para **venderse a hoteles**: cada hotel lo instala, carga sus datos (nombre, logo, color, pisos y habitaciones) en un asistente inicial y el sistema adopta su identidad.

Módulos principales:

- **Plano de habitaciones:** el estado de cada habitación (libre, ocupada, llega hoy, sale hoy, sucia, mantenimiento) de un vistazo.
- **Tape chart de reservas:** una línea de tiempo con las reservas, que se arrastran para cambiarles las fechas o la habitación.
- ABM de huéspedes, habitaciones y reservas, con check-in y check-out.
- **Sitio público del hotel** (`/`, sin login): habitaciones con visor 3D y reserva online simple (sin pago real). La reserva aparece al instante en el plano y el tape chart.

El plan completo está en [docs/plan.md](docs/plan.md) y el sistema de diseño en [design/identidad/brandbook.html](design/identidad/brandbook.html).

## Stack

- **Backend:** Python 3.12 + Flask (app factory + blueprints)
- **Base de datos:** SQLite con Flask-SQLAlchemy (se puede cambiar a PostgreSQL desde `DATABASE_URL`)
- **Frontend:** plantillas Jinja2, CSS propio con variables (`tokens.css`) y JavaScript sin frameworks

## Estructura

```
app/
  models/       modelos de la base de datos
  routes/       blueprints (una sección del sistema por archivo)
  services/     lógica de negocio e integración con APIs externas
  templates/    plantillas HTML (components/ para piezas reutilizables)
  static/       css/ (tokens y componentes), js/, img/ y brand/ (logos de Conserje)
design/         identidad del producto, brandbook y prompts de Google Stitch
docs/           plan y documentación del trabajo
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
flask --app app demo
python run.py
```

`flask --app app demo` borra la base local y carga el hotel de ejemplo "Hotel Mirador" (24 habitaciones y reservas alrededor de la fecha de hoy). Después abrir http://127.0.0.1:5000/administracion

La administración pide login. Con la demo cargada, la pantalla de ingreso muestra los usuarios de prueba (están definidos en `USUARIOS_DEMO`, en `app/demo.py`). Sin la demo, el primer usuario se crea con:

```bash
flask --app app crear-usuario
```

Para correr los tests:

```bash
python -m pytest
```
