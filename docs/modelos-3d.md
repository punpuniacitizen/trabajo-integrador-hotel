# Modelos 3D de las habitaciones

Encargo para armar en Blender (con el MCP de Blender) las ilustraciones 3D del sitio público de reservas.
Las usa la página de cada tipo de habitación (visor `<model-viewer>`) y las tarjetas (render PNG).

## Estilo

- **Diorama isométrico**: cada habitación es un bloque cortado. Hay una losa de piso con espesor y dos paredes, la del fondo y la de la izquierda, con ventanas. El frente y la derecha quedan abiertos.
- **Low poly y colores planos**, sin texturas. Los muebles salen del kit de Kenney (`design/3d/kenney-furniture/`, licencia CC0), que ya trae colores por material.
- Paleta:

  | Elemento | Color |
  |---|---|
  | Paredes | blanco cálido `#EDE7DE` |
  | Piso | madera clara `#C9A27A` |
  | Borde de la losa | verde del hotel demo `#1F6F5C` |
  | Detalles (almohadones, alfombra) | ese mismo verde o tonos tierra |

- Las cuatro habitaciones van con la **misma escala, la misma cámara y la misma luz**, así se notan los "tiers" de más chica a más grande.
- Medidas reales en metros. Los OBJ de Kenney vienen en otra escala: la `bedDouble` mide unas 9,6 × 11,3 unidades, que tienen que quedar en unos 1,6 × 2,0 m.

## Las cuatro habitaciones

| Tipo | Medida (m) | m² | Muebles (nombres del kit) |
|---|---|---|---|
| **Simple** | 3,0 × 3,6 | 11 | `bedSingle`, `sideTable` + `lampRoundTable`, `desk` + `chairDesk`, `rugRectangle`, `plantSmall1`, 1 `wallWindow` |
| **Doble estándar** | 3,6 × 4,2 | 15 | `bedDouble`, 2 × `sideTableDrawers` + `lampSquareTable`, `cabinetTelevision` + `televisionModern`, `rugRectangle`, `coatRackStanding`, 1 `wallWindow` |
| **Doble superior** | 4,2 × 4,8 | 20 | `bedDouble` con `pillow`s, 2 mesas de luz con lámparas, rincón de lectura (`loungeChairRelax` + `lampRoundFloor`), `desk` + `chairDesk`, `rugRounded`, `pottedPlant`, 1 `wallWindowSlide` (ventanal) |
| **Suite Mirador** | 6,0 × 5,0 | 30 | `bedDouble` con `pillowLong`, mesas de luz y lámparas, living (`loungeSofaLong` + `tableCoffeeGlass` + `rugRounded` + `cabinetTelevision` + `televisionModern`), baño separado por `wallHalf` (`bathtub` + `bathroomSink` + `bathroomMirror`), `pottedPlant`, `lampSquareFloor`, 2 × `wallWindowSlide` |

## Entregables

| Archivo | Para qué |
|---|---|
| `design/3d/habitaciones.blend` | Fuente editable (una escena o colección por habitación) |
| `app/static/modelos/<slug>.glb` | Visor 3D. glTF binario con transformaciones aplicadas, sin cámaras ni luces, idealmente menos de 600 KB |
| `app/static/img/habitaciones/<slug>.png` | Tarjetas. Render 1200 × 900, cámara ortográfica isométrica, fondo transparente |
| `app/static/img/habitaciones/hero.png` | Portada del sitio. Render ancho (1920 × 900) de la suite |

Slugs: `simple`, `doble-estandar`, `doble-superior`, `suite-mirador`.

Render: Eevee, una luz de sol suave de costado y luz ambiente clara. En el visor, la vista inicial imita la cámara isométrica (por ejemplo, `camera-orbit="45deg 60deg"`).

## Cómo se armaron

Todo sale de `design/3d/armar_habitaciones.py`, que se corre dentro de Blender (con el MCP o desde la consola de Python):

```python
ruta = r"<repo>\design\3d\armar_habitaciones.py"
g = {"__file__": ruta, "__name__": "__main__"}
exec(open(ruta, encoding="utf-8").read(), g)    # borra el archivo abierto y arma todo
g["renderizar"](); g["exportar"](); g["guardar"]()
```

- En el `.blend` hay una escena por habitación (con su cámara), `portada` para el hero y `Resumen`, que muestra las cuatro en fila.
- Escala del kit: 0,175. Las paredes miden 2,26 m de alto (la altura de los tramos de Kenney) y 0,14 m de espesor.
- `wallWindowSlide` es una ventana guillotina chica: para que funcione como ventanal se estira al doble de ancho.
- El baño de la suite se separa con `wallHalf` cortados a 1,1 m de alto. Con tabiques de altura completa, la cámara isométrica no lo vería.
- Las tarjetas comparten la escala de la cámara (calculada para que entre la suite), así que la simple se ve más chica a propósito.

## Después de los modelos (paso 4)

- Agregar a `TipoHabitacion`: `slug`, `metros`, `descripcion` y `comodidades`. Cargarlos en `app/demo.py`.
- Guardar `model-viewer` dentro de `app/static/vendor/`, para que funcione sin internet en la defensa.
- Armar el sitio público según `design/stitch/prompts-sitio-publico.md`.
