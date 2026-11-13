# Conserje: sistema de gestión hotelera

Trabajo integrador. **Conserje** es un software de gestión interna pensado para **venderse a hoteles**: cada hotel lo instala, carga sus datos (nombre, logo, color, pisos y habitaciones) desde Configuración y el sistema adopta su identidad.

Módulos:

- **Plano de habitaciones:** el estado de cada habitación (libre, ocupada, llega hoy, sale hoy, sucia, mantenimiento), con check-in, check-out, limpieza y mantenimiento.
- **Tape chart de reservas:** una línea de tiempo con las reservas, que se arrastran para cambiarles las fechas o la habitación.
- **Nueva reserva:** alta de reservas desde la administración, con disponibilidad en vivo y buscador de huéspedes.
- **Sitio público del hotel** (`/`, sin login): habitaciones con visor 3D y reserva online simple (sin pago real). La reserva aparece al instante en el plano y el tape chart.
- **Configuración** (solo administración): datos e identidad del hotel, ubicación en el mapa, tipos de habitación con foto y/o modelo 3D `.glb`, pisos y habitaciones, y usuarios.

Para estudiar y exponer: la [guía de estudio](docs/guia-de-estudio.html) explica cómo funciona todo con ejemplos, y el [mapa del código](docs/mapa-del-codigo.html) muestra qué hay en cada carpeta y qué se conecta con qué. Se abren con `guia-de-estudio.bat`. El sistema de diseño está en [design/identidad/brandbook.html](design/identidad/brandbook.html).

## Stack

- **Backend:** Python 3.12 + Flask (app factory + blueprints)
- **Base de datos:** SQLite con Flask-SQLAlchemy (se puede cambiar a PostgreSQL desde `DATABASE_URL`)
- **Frontend:** plantillas Jinja2, CSS propio con variables (`tokens.css`) y JavaScript sin frameworks
- **Externo:** Google Fonts (Inter), Google Maps (mapa embebido, sin clave) y `<model-viewer>` (visor 3D, guardado en `static/vendor/`)

## Estructura

```
app/
  __init__.py   create_app(): arma la aplicación y registra todo
  models/       tablas de la base (hotel, tipos y habitaciones, huéspedes, reservas, usuarios)
  routes/       blueprints: una sección del sistema por archivo (URL -> función -> plantilla o JSON)
  services/     reglas del negocio (disponibilidad, check-in, ocupación…), sin nada de HTML
  templates/    plantillas HTML (Jinja2)
  static/       css/, js/, imágenes, modelos 3D y logos de Conserje
  contexto.py   variables que reciben todas las plantillas (hotel, usuario, color, fecha)
  filtros.py    formato de fechas y montos en castellano
  demo.py       comando `demo`: carga el Hotel Mirador de ejemplo
  comandos.py   comando `crear-usuario`
design/         identidad del producto, brandbook, prompts de Google Stitch y escenas de Blender
docs/           mapa del código, plan inicial y notas de los modelos 3D
tests/          pruebas con pytest
config.py       configuración (clave secreta, base de datos, tope de subida)
run.py          punto de entrada
```

## Cómo correrlo

En Windows alcanza con hacer doble clic en **`iniciar.bat`**: prepara Python la primera vez, ofrece recargar los datos de ejemplo, levanta el servidor y abre la página. A mano:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app app demo
python run.py
```

`flask --app app demo` borra la base local y los archivos subidos, y carga el hotel de ejemplo "Hotel Mirador" (24 habitaciones, reservas alrededor de la fecha de hoy, y los renders y modelos 3D de `app/static/` como si el hotel los hubiera subido). Después abrir http://127.0.0.1:5000/administracion

La administración pide login. Con la demo cargada, la pantalla de ingreso muestra los usuarios de prueba (están definidos en `USUARIOS_DEMO`, en `app/demo.py`). Sin la demo, el primer usuario se crea con:

```bash
flask --app app crear-usuario
```

Para correr los tests:

```bash
python -m pytest
```
