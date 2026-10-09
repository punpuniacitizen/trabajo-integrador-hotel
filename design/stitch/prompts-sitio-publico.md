# Prompts para Google Stitch: sitio público de reservas

El sitio que ven los clientes del hotel. No pide login; la administración sigue en `/administracion`.
Igual que antes, las pantallas de Stitch son **referencia visual**: después se pasan a Flask + CSS + JS.

## Alcance (a propósito, simple)

La reserva es un **demostrador**: sirve para mostrar que una reserva hecha desde la web aparece en el plano y en el tape chart. No es un sistema de reservas real.

- El cliente elige **tipo de habitación, fechas, cantidad de personas y pone su nombre** (y un email opcional). Nada más.
- **No hay pago**: solo un cartel que dice que en un hotel real acá iría el pago.
- El sistema asigna una habitación libre de ese tipo. Si no hay lugar, muestra un mensaje y listo.
- No hay cuentas de cliente, emails, cancelaciones ni políticas.

| Ruta | Pantalla |
|---|---|
| `/` | Inicio: el hotel y sus habitaciones |
| `/habitaciones/<tipo>` | Una habitación con el visor 3D |
| `/reservar` | Formulario de reserva (todo en una pantalla) |
| `/reserva/<código>` | Reserva confirmada |

Exportá las pantallas como PNG en esta carpeta: `10-inicio.png`, `11-habitacion.png`, `12-reservar.png` y `13-confirmacion.png`.

---

## Contexto y sistema de diseño

```
Diseñá el sitio web público de "Hotel Mirador", un hotel chico de montaña en San Carlos de Bariloche, donde los clientes pueden ver las habitaciones y hacer una reserva simple. El sitio lo genera "Conserje", un sistema de gestión hotelera de marca blanca: la estética es limpia y neutra, y la personalidad la ponen el logo del hotel y su color. Diseñá para escritorio (1440 px), pero pensando en que se adapte a celular.

Sistema de diseño:
- Estilo: sobrio y luminoso, con mucho espacio en blanco, bordes finos de 1 px y sombras suaves.
- Tipografía: Inter. Títulos grandes en SemiBold y texto de 16 px.
- Colores: fondo #FAFAFA, tarjetas #FFFFFF, bordes #E4E4E7, texto #18181B, texto secundario #71717A.
- Acento del hotel: verde #1F6F5C, para los botones principales y los links, con texto blanco encima.
- Radios: 8 px en botones e inputs, 16 px en tarjetas e imágenes. Botones de 44 px de alto.
- Las habitaciones se muestran como ilustraciones 3D isométricas tipo "diorama" (una habitación cortada en un bloque, vista en diagonal desde arriba, estilo low poly, colores cálidos y verde) sobre fondo transparente.
- Encabezado: el logo del hotel a la izquierda (un arco con montañas en verde + "HOTEL Mirador" en una serif) y a la derecha el botón principal "Reservar".
- Pie mínimo: dirección, horarios de check-in 14:00 y check-out 10:00, y en gris chico "con Conserje · Acceso del personal".
- Todo el texto en español rioplatense (voseo). Que sea simple: no agregues pasos, cuentas, cupones, reseñas ni políticas.
```

## 10 · Inicio

```
Página de inicio. Arriba, un hero con el título "Tu lugar frente al lago", el subtítulo "Hotel Mirador · San Carlos de Bariloche", el botón principal "Reservar" y, a la derecha, una ilustración isométrica grande de la suite.
Debajo, la sección "Nuestras habitaciones" con 4 tarjetas, de la más chica a la más grande: Simple, Doble estándar, Doble superior y Suite Mirador. Cada tarjeta tiene la ilustración isométrica, el nombre, "Hasta 2 personas · 20 m²", "$ 56.000 por noche" y dos links: "Ver en 3D" y "Reservar".
Después, el pie.
```

## 11 · Habitación (visor 3D)

```
Página de una habitación, la "Doble superior". A la izquierda, ocupando más de la mitad del ancho, un visor 3D grande con la ilustración isométrica sobre fondo gris muy claro y una pista chica abajo: "Arrastrá para girar". Debajo, 4 miniaturas para pasar a las otras habitaciones.
A la derecha: el nombre, "Hasta 2 personas · 20 m²", un párrafo corto de descripción, una lista breve de lo que tiene (cama queen, sillón de lectura, escritorio), el precio "$ 56.000 por noche" y el botón principal "Reservar esta habitación".
```

## 12 · Reservar

```
Página de reserva, todo en una sola pantalla y en dos columnas.
Columna izquierda, una tarjeta "Tu reserva" con un formulario corto:
- "Habitación": 4 opciones elegibles en fila, cada una con miniatura isométrica, nombre y precio por noche (la Doble superior está seleccionada).
- "Llegada" y "Salida" (dos campos de fecha uno al lado del otro).
- "Personas" (selector de 1 a 4).
- "Nombre y apellido".
- "Email (opcional)".
Debajo del formulario, un cartel gris suave con un ícono de tarjeta: "Pago: esta es una demo, no se cobra nada. En un hotel real acá irían los datos de pago."
Y el botón principal grande "Confirmar reserva".
Columna derecha, una tarjeta de resumen chica que se actualiza sola: la miniatura de la habitación elegida, las fechas, "3 noches" y el total "$ 168.000".
Mostrá también, arriba del botón, cómo se vería un aviso de error en rojo suave: "No queda lugar en la Suite Mirador para esas fechas. Probá con otras fechas u otra habitación."
```

## 13 · Confirmación

```
Página de reserva confirmada, centrada. Un círculo verde suave con un tilde, el título "¡Listo, Lucía! Tu reserva está hecha" y el código "Reserva #0358". Debajo, una tarjeta con el resumen: la miniatura isométrica de la habitación, el nombre de la habitación, las fechas con los horarios de check-in y check-out, la cantidad de personas y el total "a pagar en el hotel". Un solo botón: "Volver al inicio".
```
