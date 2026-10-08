# Prompts para Google Stitch

Sirven para generar maquetas de referencia de las pantallas principales en [Google Stitch](https://stitch.withgoogle.com).
Las maquetas son **solo referencia visual**: la app se construye con `app/static/css/tokens.css` y `components.css`, no con el código que exporta Stitch.

## Cómo usarlos

1. Entrá a Stitch y elegí el modo **Web**.
2. Para la primera pantalla, pegá el bloque **Contexto y sistema de diseño** seguido del prompt de la pantalla.
3. Para las siguientes, pegá solo el prompt de la pantalla en el mismo proyecto, así Stitch mantiene el estilo.
4. Exportá cada pantalla como PNG en esta carpeta, con el número y el nombre del prompt (por ejemplo `03-plano.png`).

Si Stitch inventa colores o mezcla idiomas, agregá al final: *"Respetá exactamente la paleta indicada. Todo el texto de la interfaz va en español rioplatense."*

---

## Contexto y sistema de diseño

```
Diseñá pantallas de escritorio (1440 px de ancho) para "Conserje", un sistema web de gestión interna para hoteles. Es un producto de marca blanca que se vende a distintos hoteles: la interfaz tiene que ser sobria y neutra, y el protagonista es el hotel que lo usa (su logo va arriba en la barra lateral). Lo usan recepcionistas en una computadora de escritorio.

Sistema de diseño:
- Estilo: minimalista y profesional, parecido a Linear o Vercel. Mucho espacio en blanco, bordes finos de 1 px, sombras casi imperceptibles y nada decorativo.
- Tipografía: Inter. Texto base de 14 px, títulos de página de 24 px en SemiBold y números tabulares.
- Fondo de la app: #FAFAFA. Superficies (tarjetas, barra lateral): #FFFFFF. Bordes: #E4E4E7. Texto: #18181B. Texto secundario: #71717A.
- Color de acento (del hotel de ejemplo "Hotel Mirador"): verde #1F6F5C. Se usa SOLO en el botón principal, el ítem activo de la navegación y el foco. Todo lo demás es gris.
- Estados de habitación (colores fijos, siempre acompañados de texto):
  Libre #15803D · Ocupada #1D4ED8 · Llega hoy #6D28D9 · Sale hoy #C2410C · Sucia #A16207 · Mantenimiento #B91C1C.
  Cada uno tiene una versión suave de fondo (por ejemplo, Libre #DCFCE7).
- Radios: 8 px en botones e inputs, 12 px en tarjetas. Botones de 36 px de alto.
- Layout: barra lateral fija de 240 px a la izquierda (logo del hotel, navegación: Plano, Reservas, Huéspedes, Habitaciones, Configuración; abajo, el usuario y el texto chico "con Conserje"), barra superior de 56 px con el título de la página, un buscador y la fecha de hoy.
- Todo el texto en español rioplatense (voseo), corto y directo.
```

---

## 01 · Login

```
Pantalla de inicio de sesión. Centrada sobre fondo #FAFAFA, una tarjeta blanca de 400 px con el logo del hotel arriba ("Hotel Mirador": emblema de un arco con montañas en verde #1F6F5C y el nombre en una serif), el título "Ingresá a tu cuenta", campos de Email y Contraseña, el botón principal "Ingresar" a todo el ancho y el link "¿Olvidaste tu contraseña?". Debajo de la tarjeta, en gris claro y chico: "Conserje · gestión hotelera".
```

## 02 · Asistente de configuración inicial

```
Asistente que aparece la primera vez que se instala el sistema, antes de que exista un hotel configurado. No tiene barra lateral. Arriba, el logo de Conserje (una campanilla de recepción negra y la palabra "conserje") y un indicador de 4 pasos: 1 Datos del hotel · 2 Tipos de habitación · 3 Habitaciones · 4 Administrador. El paso activo es el 3, "Habitaciones".
A la izquierda, un formulario: "Desde el piso" 1, "Hasta el piso" 4, "Habitaciones por piso" 8, "Numeración" con el ejemplo "101, 102… 201, 202…", y una tabla chica para asignar el tipo por rango (01–04 Doble estándar, 05–07 Doble superior, 08 Suite).
A la derecha, una vista previa en vivo: una grilla con los 4 pisos y sus 8 habitaciones, como tarjetas chicas con el número y una inicial del tipo.
Abajo: botones "Atrás" (secundario) y "Generar 32 habitaciones" (principal). En este asistente el acento es negro #18181B porque todavía no hay hotel.
```

## 03 · Plano de habitaciones (pantalla de inicio)

```
Pantalla principal: plano de ocupación del hotel. Título "Plano de habitaciones", con un selector de fecha (hoy, 14 de octubre) y el botón principal "+ Nueva reserva".
Debajo: una fila de 4 indicadores chicos (Ocupación 72%, Llegadas hoy 6, Salidas hoy 4, Habitaciones sucias 3), una fila de filtros (Piso: Todos · Tipo · Estado) y la leyenda de colores de los estados.
Después, un bloque por piso ("Piso 1", "Piso 2", "Piso 3"), cada uno con 8 tarjetas de habitación en grilla. Cada tarjeta es blanca, con un borde superior grueso de 4 px del color de su estado, el número grande (101), el tipo chico en gris (Doble), el estado en texto de color (Ocupada) y el apellido del huésped si lo hay. Algunas tienen un círculo chico en la esquina superior derecha con "S" (sucia, amarillo) o "M" (mantenimiento, rojo). Las bloqueadas tienen un rayado diagonal gris.
A la derecha, un panel lateral abierto de 380 px con el detalle de la habitación 204 (ocupada): huésped "Lucía Fernández", fechas 12 al 16 de octubre, 4 noches, 2 personas, total $ 192.000, y los botones "Hacer check-out" (principal), "Ver reserva" y "Marcar sucia" (secundarios).
```

## 04 · Tape chart de reservas

```
Pantalla "Reservas" en modo calendario (tape chart), como el de los sistemas hoteleros profesionales. Arriba: el título, un selector "14 días / 30 días", flechas para ir atrás y adelante, el botón "Hoy" y el botón principal "+ Nueva reserva".
El cuerpo es una grilla: la primera columna fija tiene las habitaciones agrupadas por piso (número en negrita y tipo debajo, en gris), y las demás columnas son días (día de la semana abreviado arriba y número grande debajo). La columna de hoy está resaltada con un fondo verde muy suave y una línea vertical.
Las reservas son barras horizontales redondeadas de 28 px de alto que ocupan los días de la estadía, con el apellido del huésped y la cantidad de noches ("García · 5 n"). Las reservas en curso son barras azules sólidas #1D4ED8 con texto blanco; las confirmadas (futuras) son azul claro #DBEAFE con borde y texto azul; las finalizadas, gris claro.
Mostrá una barra siendo arrastrada (con sombra y cursor de mano) y un tooltip "Mover a 305 · 16 al 19 oct".
```

## 05 · Ficha de reserva

```
Página de detalle de una reserva. Arriba, la ruta "Reservas / #1042", el título "Reserva #1042" con el badge de estado "Confirmada" y, a la derecha, los botones "Hacer check-in" (principal), "Editar" y "Cancelar reserva" (rojo, fantasma).
Dos columnas. A la izquierda, una tarjeta "Estadía" (habitación 305, Doble superior, entrada 16/10/2026 desde las 14:00, salida 19/10/2026 hasta las 10:00, 3 noches, 2 adultos) y otra tarjeta "Importe" (3 noches × $ 52.000 = $ 156.000). A la derecha, una tarjeta "Huésped" con avatar de iniciales, nombre, DNI, email, teléfono y nacionalidad con bandera, y abajo una tarjeta "Notas" con un campo de texto.
Al pie, un historial chico: "Creada por Sofía (recepción) el 08/10 a las 11:32".
```

## 06 · Huéspedes

```
Pantalla "Huéspedes": un listado con buscador grande ("Buscá por nombre, documento o email") y el botón principal "+ Nuevo huésped". Una tabla con las columnas Huésped (avatar de iniciales + nombre), Documento, País (con bandera), Email, Última estadía y Reservas (número), con números tabulares y una fila resaltada al pasar el mouse. Paginación abajo a la derecha. Un huésped de la tabla tiene el badge "En el hotel" (azul).
```
