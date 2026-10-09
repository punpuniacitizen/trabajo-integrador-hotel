# Habitaciones en 3D

Las habitaciones del sitio público se arman en Blender (con el MCP de Blender) y salen de dos formas:

- **Imágenes** renderizadas con Cycles para las tarjetas, las miniaturas y la portada.
- **Modelos `.glb` con la luz horneada** para el visor `<model-viewer>` de la página de cada tipo. Cycles calcula toda la iluminación (sol, lámparas, rebotes) y la guarda en una textura; el modelo usa un material sin luz (`KHR_materials_unlit`) que la muestra tal cual, así el visor se ve como los renders desde cualquier ángulo.

## Estilo

- **Diorama isométrico**: cada habitación es un bloque cortado. Hay una losa de piso con espesor y dos paredes, la del fondo y la de la izquierda, con ventanas. El frente y la derecha quedan abiertos.
- **Low poly y cálido ("cozy")**. Los muebles salen del kit de Kenney (`design/3d/kenney-furniture/`, licencia CC0), con materiales propios:
  - piso de tablas de madera, revoque en las paredes y boiserie verde con machimbre hasta media altura;
  - telas, madera con veta y metales de latón;
  - cortinas de lino, cuadros con cerros y un lago, repisas con libros, mantas y almohadones, plantas.
- Paleta base:

  | Elemento | Color |
  |---|---|
  | Paredes | crema `#EFE3CF` |
  | Boiserie | verde `#2F6655` |
  | Piso | roble `#C6A27C` / `#AE855E` |
  | Borde de la losa | verde del hotel demo `#1F6F5C` |
  | Telas | verde, terracota, mostaza, salvia, avena y lino |

- **Luz de tarde**: un sol dorado entra por las ventanas (un techo invisible para la cámara evita que entre por arriba), las lámparas están prendidas y hay un relleno suave del lado abierto. Render con Cycles y AgX.
- Las cuatro habitaciones van con la **misma escala, la misma cámara y la misma luz**, así se notan los "tiers" de más chica a más grande.
- Medidas reales en metros (escala del kit: 0,175).

## Las cuatro habitaciones

| Tipo | Medida (m) | m² | Qué tiene |
|---|---|---|---|
| **Simple** | 3,0 × 3,6 | 11 | Cama de una plaza, mesa de luz con lámpara, escritorio con silla y repisa, biblioteca baja bajo la ventana, alfombra redonda, plantas |
| **Doble estándar** | 3,6 × 4,2 | 15 | Cama doble, 2 mesas de luz con lámparas, 2 cuadros, banco al pie de la cama, mueble con TV, perchero, alfombra, planta |
| **Doble superior** | 4,2 × 4,8 | 20 | Cama doble con almohadones, mesas de luz, cuadro, banco, rincón de lectura (sillón y lámpara de pie), escritorio con lámpara y repisa, ventanal con cortinas |
| **Suite Mirador** | 6,0 × 5,0 | 30 | Dormitorio con ventanal, baño con bañera separado por tabiques a media altura, living (sillón, sillón individual, mesa ratona, lámpara de pie), mesita para desayunar, 2 ventanales |

## Entregables

| Archivo | Para qué |
|---|---|
| `design/3d/habitaciones.blend` | Fuente editable: una escena por habitación, `portada` y `Resumen` (las cuatro en fila) |
| `app/static/modelos/<slug>.glb` | Visor 3D. Una sola malla con la luz horneada en una textura WebP y material sin luz |
| `app/static/img/habitaciones/<slug>.png` | Tarjetas, miniaturas y póster del visor. Render 1200 × 900, cámara ortográfica isométrica, fondo transparente |
| `app/static/img/habitaciones/hero.png` | Portada del sitio. Render ancho (1920 × 900) de la suite, corrida a la derecha |

Slugs: `simple`, `doble-estandar`, `doble-superior`, `suite-mirador`.

## Cómo se arman y renderizan

Todo sale de `design/3d/armar_habitaciones.py`. Para armar la escena, dentro de Blender (con el MCP o desde la consola de Python):

```python
ruta = r"<repo>\design\3d\armar_habitaciones.py"
g = {"__file__": ruta, "__name__": "__main__"}
exec(open(ruta, encoding="utf-8").read(), g)    # borra el archivo abierto y arma todo
g["guardar"]()
```

Para renderizar los cinco PNG y hornear los cuatro `.glb`, en segundo plano y con la placa de video si hay (con el procesador tarda bastante más):

```
blender -b design/3d/habitaciones.blend --python design/3d/armar_habitaciones.py -- renderizar gpu
blender -b design/3d/habitaciones.blend --python design/3d/armar_habitaciones.py -- hornear gpu muestras=512
```

A `hornear` se le pueden pasar slugs para hacer solo algunas (`hornear gpu simple`). Conviene correrlo siempre en segundo plano: en Blender 5.1 exportar desde una escena temporal pasada por contexto hace caer al programa, y el horneado tarda varios minutos.

Cómo hornea:

- Fusiona cada habitación en dos mallas (todo lo visible, y aparte las lámparas, que no tapan su propia luz), porque Cycles hornea objeto por objeto y rearmaría la escena para cada mueble. Las coordenadas locales de cada objeto se guardan como atributos para que las texturas procedurales no cambien.
- Despliega las UVs en un atlas de hasta 4096 px (unos 240 px por metro) y hornea el pase `COMBINED` sin reflejos, con un techo invisible y el vidrio que deja pasar el sol.
- Guarda la textura con el mismo AgX de los renders y exporta con `tone-mapping="none"` en el visor.

Se pierde lo que depende del ángulo de vista (los reflejos del piso). La órbita del visor se limita al lado abierto del diorama.

Notas:

- `wallWindowSlide` es una ventana guillotina chica: para que funcione como ventanal se estira al doble de ancho.
- El baño de la suite se separa con `wallHalf` cortados a 1,1 m de alto. Con tabiques de altura completa, la cámara isométrica no lo vería.
- Las tarjetas comparten la escala de la cámara (calculada para que entre la suite), así que la simple se ve más chica a propósito.
