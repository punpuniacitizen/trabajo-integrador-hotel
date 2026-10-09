# Prompts para Google Stitch: sitio público de reservas

El sitio que ven los clientes del hotel. No pide login; la administración sigue en `/administracion`.
Igual que antes, las pantallas de Stitch son **referencia visual**: después se pasan a Flask + CSS + JS.

## Estructura

| Ruta | Pantalla | Qué hace |
|---|---|---|
| `/` | Inicio | Presenta el hotel, buscador de fechas y las habitaciones por tipo |
| `/habitaciones/<tipo>` | Detalle del tipo | Visor 3D de la habitación, capacidad, comodidades y precio |
| `/reservar?entrada=…&salida=…&personas=…` | Disponibilidad | Qué tipos tienen lugar en esas fechas y cuánto sale la estadía |
| `/reservar/<tipo>?…` | Tus datos | Formulario (nombre, contacto) + pago de mentira + resumen |
| `/reserva/<código>` | Confirmación | La reserva quedó hecha; aparece en el plano y el tape chart |

Decisiones:
- El cliente elige el **tipo** de habitación, no una habitación puntual: el sistema le asigna una libre.
- El pago es un **placeholder**: no se cargan tarjetas. La reserva queda "confirmada" con saldo pendiente.
- El sitio toma la identidad del hotel (logo y color de acento), igual que la administración.
- Abajo de todo, un link discreto "Acceso del personal" lleva a `/administracion`.

Exportá las pantallas como PNG en esta carpeta: `10-inicio.png`, `11-habitacion.png`, `12-disponibilidad.png`, `13-datos.png`, `14-confirmacion.png`.

---

## Contexto y sistema de diseño

```
Diseñá el sitio web público de reservas de "Hotel Mirador", un hotel boutique de montaña en San Carlos de Bariloche. El sitio lo genera "Conserje", un sistema de gestión hotelera de marca blanca: la estética es limpia y neutra, y la personalidad la ponen el logo del hotel y su color de acento. Lo usan huéspedes desde el celular y la computadora: diseñá la versión de escritorio (1440 px) cuidando que se adapte bien a celular.

Sistema de diseño:
- Estilo: hotel boutique moderno, sobrio y luminoso. Mucho espacio en blanco, fotos/ilustraciones grandes, bordes finos de 1 px y sombras suaves. Nada recargado.
- Tipografía: Inter. Títulos grandes y livianos (SemiBold, interletrado levemente negativo), texto de 16 px.
- Colores: fondo #FAFAFA, superficies #FFFFFF, bordes #E4E4E7, texto #18181B, secundario #71717A.
- Acento del hotel: verde #1F6F5C, para botones principales, links y detalles. Texto blanco sobre el acento.
- Radios: 8 px en botones e inputs, 16 px en tarjetas e imágenes. Botones de 44 px de alto.
- Las habitaciones se muestran como ilustraciones 3D isométricas tipo "diorama" (una habitación cortada en un bloque, vista desde arriba en diagonal, estilo low poly con colores cálidos y suaves). Usá ese estilo en todas las imágenes de habitaciones.
- Encabezado: logo del hotel a la izquierda (un arco con montañas en verde + "HOTEL Mirador" en una serif), links "Habitaciones" y "Cómo llegar", y a la derecha el botón principal "Reservar".
- Pie: dirección, horarios de check-in (14:00) y check-out (10:00), teléfono, y en gris chico "con Conserje · Acceso del personal".
- Todo el texto en español rioplatense (voseo), cálido pero directo.
```

## 10 · Inicio

```
Página de inicio. Arriba, un hero de ancho completo con una ilustración isométrica grande de la suite del hotel sobre un fondo de montañas suaves, el título "Tu lugar frente al lago" y el subtítulo "Hotel Mirador · San Carlos de Bariloche". Sobre el borde inferior del hero, flotando, una barra de búsqueda blanca con sombra: "Llegada" (fecha), "Salida" (fecha), "Huéspedes" (selector 1 a 4) y el botón principal "Ver disponibilidad".
Debajo, la sección "Nuestras habitaciones" con 4 tarjetas en fila, de la más chica a la más grande: Simple, Doble estándar, Doble superior y Suite Mirador. Cada tarjeta tiene la ilustración isométrica de la habitación, el nombre, íconos chicos con la capacidad y los metros cuadrados, el texto "desde $ 38.000 por noche" y un link "Ver en 3D".
Después, una franja con 3 comodidades del hotel (Desayuno incluido, Wi-Fi, Estacionamiento) con íconos de línea, y el pie.
```

## 11 · Detalle de una habitación (visor 3D)

```
Página de detalle de la "Doble superior". A la izquierda, ocupando 60% del ancho, un visor 3D grande con la habitación isométrica sobre fondo gris muy claro, con una pista chica abajo: "Arrastrá para girar · Rueda para acercar", y debajo 3 miniaturas para cambiar de habitación (las otras categorías).
A la derecha: el nombre "Doble superior", una línea "Hasta 2 personas · 24 m² · Vista al lago", un párrafo corto de descripción, una lista de comodidades con íconos de línea (cama queen, sillón de lectura, escritorio, baño con ducha, frigobar, calefacción), el precio "$ 56.000 por noche" grande y el botón principal "Elegir fechas". Debajo, en gris chico: "Check-in desde las 14:00 · Check-out hasta las 10:00".
```

## 12 · Disponibilidad

```
Página de resultados de disponibilidad. Arriba, la barra de búsqueda compacta con lo elegido (16 oct → 19 oct · 3 noches · 2 huéspedes) y el botón "Cambiar".
Debajo, una lista vertical de tarjetas horizontales, una por tipo de habitación: a la izquierda la ilustración isométrica, al centro el nombre, la capacidad y 3 comodidades, y a la derecha el total "$ 168.000 por 3 noches" con el desglose chico "$ 56.000 × 3 noches" y el botón principal "Elegir". Una tarjeta muestra un aviso naranja chico "¡Quedan 2!". La tarjeta de la "Simple" está atenuada con el texto "Es para 1 persona" y la de la "Suite Mirador" dice "Sin disponibilidad para esas fechas" con el botón deshabilitado.
```

## 13 · Tus datos

```
Página para completar la reserva, en dos columnas. Arriba, un indicador de pasos: 1 Fechas ✓ · 2 Habitación ✓ · 3 Tus datos.
Columna izquierda (más ancha): tarjeta "Tus datos" con Nombre, Apellido, Email, Teléfono y Documento (opcional), y un campo "¿Algo que tengamos que saber?" (comentarios). Debajo, una tarjeta "Pago" con un aviso: "Esta es una demo: no se cobra nada. En un hotel real acá irían los datos de la tarjeta." y campos de tarjeta deshabilitados en gris (número, vencimiento, código). Al final, el botón principal grande "Confirmar reserva" y una línea chica de condiciones de cancelación.
Columna derecha, fija al hacer scroll: tarjeta de resumen con la miniatura isométrica de la habitación, "Doble superior", fechas "Jue 16 oct → Dom 19 oct", "3 noches · 2 huéspedes", el desglose y el total "$ 168.000" destacado.
```

## 14 · Confirmación

```
Página de reserva confirmada. Centrado, un círculo verde suave con un tilde, el título "¡Listo, Lucía! Tu reserva está confirmada" y el código grande "Reserva #0358". Debajo, una tarjeta con el resumen: habitación (con miniatura isométrica), fechas con horarios de check-in y check-out, huéspedes, total y "Saldo a pagar en el hotel". Dos botones: "Ver cómo llegar" (secundario) y "Volver al inicio" (principal). Un texto chico: "Te mandamos los detalles a lucia@example.com" (no se envía nada de verdad en la demo).
```
