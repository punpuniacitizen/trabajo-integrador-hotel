# Plan: sistema de gestión hotelera "marca blanca" (Flask)

## Contexto

Trabajo integrador del colegio: una web de gestión interna hecha con Flask, HTML, CSS y JS, con SQLite.
Después de hablar con el profe, el sistema pasa a ser un **producto que se vende a cualquier hotel**, no el sistema de un hotel en particular. Por eso:

- La identidad visual es **neutra, de producto** ("medio X"). Cada hotel que lo instala pone su nombre, su logo y su color de acento.
- **Modelo instalable:** cada hotel tiene su propia instalación. La primera vez que se abre, un asistente pide los datos del hotel y genera sus habitaciones.
- **Módulos visuales elegidos:** plano de habitaciones y tape chart de reservas, además del ABM básico.

Ya está hecho: repo privado https://github.com/punpuniacitizen/trabajo-integrador-hotel con el esqueleto (`app/` con `models/`, `routes/`, `services/`, `templates/` y `static/`; además `design/`, `docs/`, `scripts/`, `tests/`, `config.py` y `run.py`).

Nombre provisorio del producto: **Conserje** (alternativas: Hospeda, Recepta). Se define en el paso 1.

---

## Paso 1: identidad del producto y Stitch

Objetivo: un sistema de diseño sobrio que funcione bien con cualquier logo o color de hotel.

1. **Logo del producto en SVG vectorial** (lo dibujo yo a mano): isotipo de una campanilla de recepción geométrica, en estas versiones:
   - `isotipo.svg`, `logo-horizontal.svg` y `logo-vertical.svg`
   - `logo-mono.svg` (negro) y `logo-negativo.svg` (blanco)
   - `favicon.svg`

   Van en `design/identidad/` y se copian a `app/static/brand/`.
2. **Paleta**
   - Escala de grises neutros del 50 al 900.
   - **Un solo color de acento por defecto**, que cada hotel reemplaza.
   - Colores semánticos fijos para los estados de las habitaciones (libre, ocupada, llega hoy, sale hoy, sucia, mantenimiento). Nunca dependen del acento, así no chocan con el color del hotel.
3. **Tipografía:** Inter desde Google Fonts, con números tabulares para el tape chart.
4. **Tokens** en `app/static/css/tokens.css`: colores, espaciado, radios, sombras y tipografía, como variables CSS.
5. **Brandbook** en `design/identidad/brandbook.html`: logo, paleta, tipografía, estados y componentes (botones, inputs, badges, tarjetas). Opcional: publicarlo como página para mostrárselo al profe.
6. **Stitch:** escribo `design/stitch/prompts.md` con el sistema de diseño y un prompt por pantalla:
   - Login
   - Asistente de configuración
   - Plano de habitaciones
   - Tape chart
   - Ficha de reserva
   - Listado de huéspedes

   Vos lo pegás en Google Stitch (o lo manejo yo en el navegador integrado si iniciás sesión ahí). Las capturas exportadas van a `design/stitch/` y sirven **solo como referencia**: el CSS se escribe a mano a partir de los tokens.
7. **Hotel demo para la defensa:** "Hotel Demo" con un logo SVG simple y otro color de acento, para mostrar que el sistema cambia de identidad.

## Paso 2: base de la aplicación

- `app/extensions.py`: `db` (Flask-SQLAlchemy) y `login_manager` (Flask-Login). Se inicializan en `create_app()` (`app/__init__.py`), que hoy tiene una ruta provisoria.
- Blueprints en `app/routes/`: `auth`, `setup`, `plano`, `reservas`, `huespedes`, `habitaciones` y `api` (JSON para el JS).
- `templates/base.html`:
  - Barra lateral con el logo del hotel, barra superior y un pie que dice "con Conserje".
  - Se inyecta `--color-accent` desde la configuración del hotel con un `context_processor`. Las variantes hover y suave salen de `color-mix()`.
- Login con roles **admin** (configuración, tarifas y usuarios) y **recepción** (operación diaria).

### Modelos (`app/models/`)

| Modelo | Campos clave |
|---|---|
| `ConfiguracionHotel` (fila única) | nombre, logo, color_acento, ciudad, moneda, hora_checkin, hora_checkout, setup_completo |
| `Usuario` | nombre, email, password_hash, rol |
| `TipoHabitacion` | nombre, capacidad, tarifa_base |
| `Habitacion` | numero, piso, tipo_id, estado_limpieza (limpia/sucia), fuera_de_servicio, nota_mantenimiento |
| `Huesped` | nombre, apellido, documento, email, teléfono, país |
| `Reserva` | huesped_id, habitacion_id, entrada, salida, personas, estado (confirmada / en curso / finalizada / cancelada), total, notas |

La ocupación (libre, ocupada, llega hoy, sale hoy) **no se guarda: se calcula** a partir de las reservas. En la base solo se guarda el estado físico (limpieza y mantenimiento).

## Paso 3: asistente de configuración inicial (lo que lo hace "vendible")

Si `setup_completo` está en falso, toda ruta redirige a `/setup`:

1. Datos del hotel, logo (se guarda en `instance/uploads/` y se sirve con una ruta) y color de acento, con vista previa en vivo.
2. Tipos de habitación y tarifas.
3. **Generador de habitaciones:** "pisos 1 a 4, 8 habitaciones por piso, numeración 101…", con tipo asignable por rango.
4. Creación del usuario administrador.

Después, todo se puede editar desde **Configuración** (solo admin).

## Paso 4: ABM y lógica de reservas

- Huéspedes: alta, búsqueda y ficha con su historial de reservas.
- Reservas: alta, edición, cancelación, **check-in** (pasa a "en curso") y **check-out** (pasa a "finalizada" y la habitación queda **sucia**).
- Validación central en `app/services/reservas.py`: no se permiten superposiciones en la misma habitación (`entrada < otra.salida and salida > otra.entrada`, sin contar las canceladas). La usan tanto los formularios como la API.
- El total se calcula como noches × tarifa del tipo.

## Paso 5: plano de habitaciones (página de inicio)

- Una grilla por piso **generada a partir de la base**. Cada habitación es una tarjeta con su número, tipo y color de estado, y un ícono si está sucia o en mantenimiento.
- Leyenda y filtros por piso, tipo y estado, más un selector de fecha para ver la ocupación de otro día.
- Al hacer clic se abre un panel lateral (`fetch /api/habitaciones/<id>`) con el huésped actual y la próxima reserva. Desde ahí: check-in, check-out, marcar limpia o sucia y mantenimiento.
- Archivos: `templates/plano.html`, `static/js/plano.js` y `static/css/plano.css`.

## Paso 6: tape chart de reservas

- Grilla CSS: **filas = habitaciones** (agrupadas por piso) y **columnas = días** (ventana de 14 o 30 días con navegación). Cada reserva es una barra ubicada con `grid-column`, coloreada según su estado, y hay una línea que marca el día de hoy.
- **Arrastrar** una barra la cambia de fechas o de habitación. **Estirar** su borde derecho alarga la estadía. Usa *pointer events* en JS puro, con ajuste a la grilla.
- Al soltar se manda un `PATCH /api/reservas/<id>`, que valida con el mismo servicio del paso 4. Si hay conflicto, la barra vuelve a su lugar y aparece un aviso.
- Arrastrar sobre celdas vacías abre el formulario de nueva reserva con las fechas y la habitación ya cargadas.
- Archivos: `templates/tapechart.html`, `static/js/tapechart.js` y `static/css/tapechart.css`.

## Paso 7: datos demo, APIs externas y pulido

- `flask demo`: un comando que carga el "Hotel Demo" con unas 40 habitaciones, huéspedes de prueba (generados en el script o con randomuser.me) y reservas repartidas en ±30 días. Así la defensa siempre arranca con datos lindos.
- APIs externas chicas, cacheadas en `app/services/`:
  - **REST Countries** para el selector de país del huésped con su bandera.
  - **Open-Meteo** para el clima de la ciudad del hotel en la barra superior. No necesita clave.
- Que se vea bien en celular (al menos el plano y las fichas), con estados vacíos y mensajes flash.
- Extras si sobra tiempo: landing del producto ("vendé tu hotel con Conserje"), consumos o facturación, modo oscuro, reportes.

## Paso 8: documentación

`README.md` (instalación y capturas), `docs/` con el diagrama de la base y las decisiones de diseño, y un guion para la defensa.

---

## Verificación

- **Tests** (`tests/`, con pytest):
  - Validación de superposición: casos de borde, como el mismo día de salida y entrada, que **sí** está permitido.
  - Que el asistente redirija mientras `setup_completo` esté en falso.
  - Que check-in y check-out cambien bien los estados.
  - Que el `PATCH` de la API rechace conflictos.
- **Prueba manual** con `.claude/launch.json` y el navegador integrado:
  - Instalación desde cero → asistente → plano vacío.
  - `flask demo` → plano con datos → arrastrar en el tape chart → probar un conflicto.
  - Cambiar el color y el logo en Configuración y ver que todo cambia de tema.
- Un commit por paso, que se sube a GitHub.
