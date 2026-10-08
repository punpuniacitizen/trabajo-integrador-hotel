# Diseño

Material de diseño del producto. La app no lo usa directamente.

- `identidad/brandbook.html`: sistema de diseño de Conserje (logo, color, tipografía, componentes, módulos, marca blanca y voz). Usa los mismos `tokens.css` y `components.css` que la app, así que para verlo bien hay que abrirlo desde un servidor que sirva la raíz del repo (por ejemplo, `python -m http.server 8765` y entrar a `http://localhost:8765/design/identidad/brandbook.html`).
- `identidad/logos/`: logos de Conserje en SVG (horizontal, vertical, isotipo, ícono, favicon, monocromo y negativo). El texto está convertido a curvas, así que no hace falta tener la fuente instalada. Los que usa la web se copian a `app/static/brand/`.
- `identidad/hotel-demo/`: logo del hotel ficticio "Hotel Mirador", que se usa para mostrar la marca blanca en la demo.
- `stitch/`: prompts para Google Stitch y las pantallas exportadas, que son solo referencia.
