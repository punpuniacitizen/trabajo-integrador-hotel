"""Arma en Blender las cuatro habitaciones de docs/modelos-3d.md.

Se corre dentro de Blender (por ejemplo, desde el MCP de Blender):

    ruta = r"...\\design\\3d\\armar_habitaciones.py"
    exec(open(ruta, encoding="utf-8").read(), {"__file__": ruta, "__name__": "__main__"})

Borra todo lo que haya en el archivo abierto y lo vuelve a armar. Después se puede llamar a
renderizar(), exportar() y guardar() para generar los entregables.
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KIT = os.path.join(RAIZ, "design", "3d", "kenney-furniture")
BLEND = os.path.join(RAIZ, "design", "3d", "habitaciones.blend")
MODELOS = os.path.join(RAIZ, "app", "static", "modelos")
IMAGENES = os.path.join(RAIZ, "app", "static", "img", "habitaciones")

ESCALA = 0.175          # unidades de Kenney -> metros (la bedDouble queda en 1,67 x 1,97 m)
PARED_KENNEY = 0.0875   # espesor de las paredes del kit, ya en metros
TRAMO = 1.75            # largo de un tramo de pared del kit (wall, wallWindow...)
ESPESOR = 0.14          # espesor de las paredes del diorama
LOSA = 0.18             # espesor de la losa del piso
VENTANAL = 2.0          # cuánto se ensancha wallWindowSlide (una ventana guillotina chica) para que sea un ventanal

# Paleta en hex (sRGB). Blender trabaja en lineal, así que se convierte al crear los materiales.
PALETA = {
    "pared": "EDE7DE",
    "piso": "C9A27A",
    "borde": "1F6F5C",
    "verde": "1F6F5C",
    "tierra": "B5714F",
    "tierra_oscura": "8E553B",
    "arena": "D9C3A5",
    "piso_bano": "DCD8D0",
    "pantalla": "34403F",
}
# Colores de los materiales del kit de Kenney, ajustados a la paleta cálida.
COLORES_KIT = {
    "_defaultMat": "EDE7DE",
    "wood": "B98B5E",
    "woodDark": "8C6243",
    "carpet": "B5714F",
    "carpetDarker": "8E553B",
    "carpetWhite": "F7F4EE",
    "metal": "B4B0A8",
    "metalDark": "3A3F40",
    "metalLight": "E6E8E4",
    "metalMedium": "6B6F70",
    "glass": "B9D6D8",
    "lamp": "F4DFA1",
    "plant": "5FA36F",
    "fur": "A5754C",
}

# Paso de la cámara isométrica: mira hacia -X, +Y y hacia abajo, así se ven las paredes
# del fondo (+Y) y de la izquierda (-X) desde adentro.
ROT_CAMARA = (math.radians(54.7356), 0.0, math.radians(45.0))
HACIA_CAMARA = Vector((1.0, -1.0, 1.0)).normalized()


# ---------------------------------------------------------------- utilidades

def lineal(hex_color):
    """'EDE7DE' -> (r, g, b, 1) en espacio lineal."""
    def canal(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (canal(hex_color[0:2]), canal(hex_color[2:4]), canal(hex_color[4:6]), 1.0)


def pintar(material, hex_color):
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = lineal(hex_color)
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    material.diffuse_color = lineal(hex_color)


def material(nombre):
    """Material de la paleta (se crea la primera vez)."""
    m = bpy.data.materials.get(nombre)
    if m is None:
        m = bpy.data.materials.new(nombre)
        pintar(m, PALETA[nombre])
    return m


def limpiar():
    """Deja el archivo vacío: una sola escena, sin objetos ni datos sueltos."""
    escena = bpy.context.window.scene
    for s in list(bpy.data.scenes):
        if s != escena:
            bpy.data.scenes.remove(s)
    for coleccion in (bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.materials,
                      bpy.data.cameras, bpy.data.lights):
        for d in list(coleccion):
            coleccion.remove(d)
    escena.name = "Resumen"
    return escena


# ---------------------------------------------------------------- kit de Kenney

_kit = {}


def cargar(nombre):
    """Importa un OBJ del kit una sola vez y deja la malla en metros, Z arriba,
    apoyada en z = 0 y centrada en planta. Los tramos de pared quedan centrados en su espesor."""
    if nombre in _kit:
        return _kit[nombre]
    antes = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(KIT, nombre + ".obj"),
                          mtl_name_collision_mode="REFERENCE_EXISTING")
    obj = next(o for o in bpy.data.objects if o not in antes)
    malla = obj.data
    malla.transform(Matrix.Scale(ESCALA, 4) @ obj.matrix_basis)
    bpy.data.objects.remove(obj)

    xs = [v.co.x for v in malla.vertices]
    ys = [v.co.y for v in malla.vertices]
    zs = [v.co.z for v in malla.vertices]
    centro_y = PARED_KENNEY / 2 if nombre.startswith("wall") else -(min(ys) + max(ys)) / 2
    malla.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, centro_y, -min(zs))))
    malla.name = "kit_" + nombre

    for m in malla.materials:
        if m and not m.get("conserje"):
            pintar(m, COLORES_KIT.get(m.name, "FF00FF"))
            m["conserje"] = True
    if nombre.startswith("wall"):
        # Los tramos de pared del kit tienen una cara gris oscura (metalDark): las dos caras van blancas
        for i, m in enumerate(malla.materials):
            if m and m.name in ("metalDark", "_defaultMat"):
                malla.materials[i] = material("pared")
    _kit[nombre] = malla
    return malla


# ---------------------------------------------------------------- habitaciones

class Habitacion:
    """Diorama de ancho x fondo (medidas interiores, en metros) centrado en el origen.
    La pared del fondo está en +Y y la de la izquierda en -X; el frente (-Y) y la derecha (+X)
    quedan abiertos."""

    def __init__(self, slug, titulo, ancho, fondo):
        self.slug, self.titulo, self.ancho, self.fondo = slug, titulo, ancho, fondo
        self.coleccion = bpy.data.collections.new(titulo)
        self.losa()

    # -- piezas sueltas

    def objeto(self, nombre, malla, ubicacion, rot=0.0, escala=(1, 1, 1)):
        obj = bpy.data.objects.new(nombre, malla)
        obj.location = ubicacion
        obj.rotation_euler = (0, 0, math.radians(rot))
        obj.scale = escala
        self.coleccion.objects.link(obj)
        return obj

    def mueble(self, nombre, x, y, rot=0.0, z=0.0, escala=1.0, telas=None, inclinar=0.0):
        """Coloca un mueble del kit. rot = 0 mira a +Y, 180 a -Y (a la cámara),
        -90 a +X y 90 a -X. telas reemplaza materiales del kit por los de la paleta."""
        malla = cargar(nombre)
        if telas:
            malla = malla.copy()
            for i, m in enumerate(malla.materials):
                if m and m.name in telas:
                    malla.materials[i] = material(telas[m.name])
        if isinstance(escala, (int, float)):
            escala = (escala,) * 3
        obj = self.objeto(nombre, malla, (x, y, z), rot, escala)
        obj.rotation_euler.x = math.radians(inclinar)  # XYZ: primero se inclina y después se gira
        return obj

    def contra_pared(self, nombre, pared, a_lo_largo, **kw):
        """Mueble con la espalda contra la pared del fondo o la de la izquierda.
        a_lo_largo es la coordenada sobre la pared (x en el fondo, y en la izquierda)."""
        malla = cargar(nombre)
        esc = kw.get("escala", 1.0)
        esc_y = esc if isinstance(esc, (int, float)) else esc[1]
        prof = max(v.co.y for v in malla.vertices) * 2 * esc_y
        sep = kw.pop("separacion", 0.02)
        if pared == "fondo":
            return self.mueble(nombre, a_lo_largo, self.fondo / 2 - prof / 2 - sep, rot=180, **kw)
        return self.mueble(nombre, -self.ancho / 2 + prof / 2 + sep, a_lo_largo, rot=-90, **kw)

    # -- estructura

    def losa(self):
        a, f = self.ancho, self.fondo
        x0, x1, y0, y1 = -a / 2 - ESPESOR, a / 2, -f / 2, f / 2 + ESPESOR
        malla = bpy.data.meshes.new(f"losa_{self.slug}")
        v = [(x0, y0, -LOSA), (x1, y0, -LOSA), (x1, y1, -LOSA), (x0, y1, -LOSA),
             (x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
        caras = [(4, 5, 6, 7), (0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        malla.from_pydata(v, [], caras)
        malla.materials.append(material("piso"))
        malla.materials.append(material("borde"))
        for i, cara in enumerate(malla.polygons):
            cara.material_index = 0 if i == 0 else 1
        self.objeto("Losa", malla, (0, 0, 0))

    def pared(self, lado, aberturas=()):
        """Arma la pared del fondo o la de la izquierda con tramos del kit.
        aberturas: [(centro, pieza, ensanche)], el resto se rellena con 'wall' estirado."""
        a, f = self.ancho, self.fondo
        if lado == "fondo":
            inicio, fin, rot = -a / 2 - ESPESOR, a / 2, 0
            ubicar = lambda c: (c, f / 2 + ESPESOR / 2, 0)
        else:
            inicio, fin, rot = -f / 2, f / 2, 90
            ubicar = lambda c: (-a / 2 - ESPESOR / 2, c, 0)
        grosor = ESPESOR / PARED_KENNEY
        cursor = inicio
        tramos = sorted(aberturas) + [(None, None, None)]
        for centro, pieza, ensanche in tramos:
            hasta = fin if centro is None else centro - TRAMO * ensanche / 2
            if hasta - cursor > 0.01:
                largo = hasta - cursor
                self.objeto(f"Pared {lado}", cargar("wall"), ubicar(cursor + largo / 2), rot,
                            (largo / TRAMO, grosor, 1))
            if centro is None:
                break
            self.objeto(f"{pieza} {lado}", cargar(pieza), ubicar(centro), rot, (ensanche, grosor, 1))
            cursor = centro + TRAMO * ensanche / 2

    def tabique(self, x0, y0, x1, y1, alto=1.1, espesor=0.1):
        """Media pared interior (wallHalf estirado), cortada a media altura para que se vea adentro."""
        largo = math.hypot(x1 - x0, y1 - y0)
        rot = math.degrees(math.atan2(y1 - y0, x1 - x0))
        self.objeto("Tabique", cargar("wallHalf"), ((x0 + x1) / 2, (y0 + y1) / 2, 0), rot,
                    (largo / (TRAMO / 2), espesor / PARED_KENNEY, alto / 2.2575))

    def parche(self, nombre, x0, y0, x1, y1, mat):
        """Rectángulo apenas por encima del piso (por ejemplo, el piso del baño)."""
        malla = bpy.data.meshes.new(nombre)
        malla.from_pydata([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [], [(0, 1, 2, 3)])
        malla.materials.append(material(mat))
        return self.objeto(nombre, malla, (0, 0, 0.004))

    def limites(self):
        """Caja que envuelve la habitación (para encuadrar la cámara)."""
        puntos = []
        for o in self.coleccion.objects:
            puntos += [o.matrix_basis @ Vector(c) for c in o.bound_box]
        mn = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
        mx = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
        return mn, mx


# Alturas de apoyo
MESA_LUZ = (0.55, 1.0, 0.75)    # sideTable del kit achicada a mesa de luz (0,52 x 0,39 x 0,50 m)
SOBRE_MESA_LUZ = 0.67 * 0.75
SOBRE_ESCRITORIO = 0.67
SOBRE_MUEBLE_TV = 0.54
COLCHON = 0.44
CAMA = {"carpet": "verde"}                          # frazada verde, sábanas blancas
ALFOMBRA = {"carpet": "tierra", "carpetDarker": "tierra_oscura"}
ALMOHADON = {"carpet": "tierra"}
TAPIZADO = {"carpet": "verde"}
PANTALLA = {"metal": "pantalla"}


def mesas_de_luz(h, cama_x, ancho_cama, lampara, modelo="sideTableDrawers"):
    for lado in (-1, 1):
        x = cama_x + lado * (ancho_cama / 2 + 0.05 + 0.26)
        h.contra_pared(modelo, "fondo", x, escala=MESA_LUZ)
        h.contra_pared(lampara, "fondo", x, z=SOBRE_MESA_LUZ, separacion=0.1)


def simple():
    h = Habitacion("simple", "Simple", 3.0, 3.6)
    h.pared("fondo")
    h.pared("izquierda", [(0.45, "wallWindow", 1.0)])
    h.mueble("bedSingle", -1.5 + 0.02 + 0.5, 1.8 - 0.02 - 0.985, rot=180, telas=CAMA)
    h.contra_pared("sideTable", "fondo", -0.17, escala=MESA_LUZ)
    h.contra_pared("lampRoundTable", "fondo", -0.17, z=SOBRE_MESA_LUZ, separacion=0.08)
    h.contra_pared("desk", "fondo", 0.82)
    h.mueble("chairDesk", 0.75, 0.95, rot=10, telas=TAPIZADO)
    h.contra_pared("plantSmall1", "fondo", 1.3, z=SOBRE_ESCRITORIO, separacion=0.12)
    h.mueble("rugRectangle", 0.3, -0.6, escala=0.6, telas=ALFOMBRA)
    return h


def doble_estandar():
    h = Habitacion("doble-estandar", "Doble estándar", 3.6, 4.2)
    h.pared("fondo")
    h.pared("izquierda", [(0.55, "wallWindow", 1.0)])
    cama_x = -0.25
    h.mueble("bedDouble", cama_x, 2.1 - 0.02 - 0.985, rot=180, telas=CAMA)
    mesas_de_luz(h, cama_x, 1.67, "lampSquareTable")
    h.contra_pared("cabinetTelevision", "izquierda", -1.25)
    h.contra_pared("televisionModern", "izquierda", -1.25, z=SOBRE_MUEBLE_TV, separacion=0.1, telas=PANTALLA)
    h.mueble("coatRackStanding", 1.45, 1.75)
    h.mueble("rugRectangle", cama_x, -0.45, escala=0.75, telas=ALFOMBRA)
    return h


def doble_superior():
    h = Habitacion("doble-superior", "Doble superior", 4.2, 4.8)
    h.pared("fondo")
    h.pared("izquierda", [(-0.1, "wallWindowSlide", VENTANAL)])
    cama_x, cama_y = -0.45, 2.4 - 0.02 - 0.985
    h.mueble("bedDouble", cama_x, cama_y, rot=180, telas=CAMA)
    for dx in (-0.36, 0.36):
        h.mueble("pillow", cama_x + dx, cama_y + 0.62, rot=180, z=COLCHON, inclinar=15, telas=ALMOHADON)
    mesas_de_luz(h, cama_x, 1.67, "lampRoundTable")
    h.mueble("loungeChairRelax", 1.4, 1.25, rot=150, telas=ALMOHADON)
    h.mueble("lampRoundFloor", 1.85, 2.15)
    h.contra_pared("desk", "izquierda", -1.75)
    h.mueble("chairDesk", -1.3, -1.75, rot=90, telas=TAPIZADO)
    h.contra_pared("pottedPlant", "izquierda", 1.6)
    h.mueble("rugRounded", -0.3, -0.35, escala=0.9, telas=ALFOMBRA)
    return h


def suite_mirador():
    h = Habitacion("suite-mirador", "Suite Mirador", 6.0, 5.0)
    h.pared("fondo", [(0.75, "wallWindowSlide", VENTANAL)])
    h.pared("izquierda", [(-0.75, "wallWindowSlide", VENTANAL)])

    # Baño en el rincón del fondo a la izquierda, con tabiques a media altura
    h.parche("Piso baño", -3.0, 0.6, -0.8, 2.5, "piso_bano")
    h.tabique(-0.8, 0.55, -0.8, 2.5)
    h.tabique(-3.0, 0.6, -1.85, 0.6)
    h.contra_pared("bathtub", "izquierda", 1.575, escala=0.88, separacion=0.01)
    h.contra_pared("bathroomSink", "fondo", -1.45)
    h.contra_pared("bathroomMirror", "fondo", -1.45, z=1.12, separacion=0.0)

    # Dormitorio
    cama_x, cama_y = 0.75, 2.5 - 0.02 - 0.985
    h.mueble("bedDouble", cama_x, cama_y, rot=180, telas=CAMA)
    h.mueble("pillowLong", cama_x, cama_y + 0.62, rot=180, z=COLCHON, inclinar=15, telas=ALMOHADON)
    mesas_de_luz(h, cama_x, 1.67, "lampSquareTable")
    h.mueble("pottedPlant", 2.7, 2.2)

    # Living
    h.contra_pared("loungeSofaLong", "izquierda", -1.05, telas=TAPIZADO)
    h.mueble("lampSquareFloor", -2.8, -2.25)
    h.mueble("rugRounded", -1.45, -1.05, rot=90, escala=0.85, telas=ALFOMBRA)
    h.mueble("tableCoffeeGlass", -1.45, -1.05, rot=90)
    h.mueble("cabinetTelevision", 0.4, -1.05, rot=90)
    h.mueble("televisionModern", 0.45, -1.05, rot=90, z=SOBRE_MUEBLE_TV, telas=PANTALLA)
    return h


HABITACIONES = [simple, doble_estandar, doble_superior, suite_mirador]


# ---------------------------------------------------------------- escenas, cámara y luz

def configurar_render(escena, ancho, alto, archivo):
    try:
        escena.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    escena.render.resolution_x, escena.render.resolution_y = ancho, alto
    escena.render.resolution_percentage = 100
    escena.render.film_transparent = True
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGBA"
    escena.render.filepath = archivo
    escena.eevee.taa_render_samples = 64
    escena.eevee.use_shadows = True
    escena.eevee.use_fast_gi = True
    try:
        escena.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    escena.view_settings.look = "None"


def camara(nombre, datos, centro, escena):
    obj = bpy.data.objects.new(nombre, datos)
    obj.rotation_euler = ROT_CAMARA
    obj.location = centro + HACIA_CAMARA * 30
    escena.collection.objects.link(obj)
    escena.camera = obj
    return obj


def proyeccion(mn, mx):
    """Ancho y alto que ocupa una caja vista desde la cámara isométrica."""
    rot = Matrix.Rotation(ROT_CAMARA[2], 3, "Z") @ Matrix.Rotation(ROT_CAMARA[0], 3, "X")
    derecha, arriba = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    esquinas = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    us = [c.dot(derecha) for c in esquinas]
    vs = [c.dot(arriba) for c in esquinas]
    return max(us) - min(us), max(vs) - min(vs)


def armar():
    resumen = limpiar()
    mundo = bpy.data.worlds.get("Ambiente") or bpy.data.worlds.new("Ambiente")
    mundo.use_nodes = True
    fondo = next(n for n in mundo.node_tree.nodes if n.type == "BACKGROUND")
    fondo.inputs[0].default_value = lineal("F2F0EC")
    fondo.inputs[1].default_value = 0.75

    luz = bpy.data.collections.new("Iluminación")
    sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", "SUN"))
    sol.data.energy = 2.2
    sol.data.angle = math.radians(14)
    sol.data.color = (1.0, 0.97, 0.92)
    # Entra desde la derecha y un poco del frente: ilumina de lleno la pared izquierda
    # y deja la del fondo un tono más oscuro, con sombras hacia las paredes.
    sol.rotation_euler = Vector((0.62, -0.38, 0.69)).to_track_quat("Z", "Y").to_euler()
    luz.objects.link(sol)

    habitaciones = [f() for f in HABITACIONES]

    # Misma escala de cámara para las cuatro, calculada para que entre la suite en 4:3
    ancho_p, alto_p = proyeccion(*habitaciones[-1].limites())
    iso = bpy.data.cameras.new("Cámara isométrica")
    iso.type = "ORTHO"
    iso.ortho_scale = max(ancho_p, alto_p * 4 / 3) * 1.08
    iso.clip_end = 100

    for h in habitaciones:
        escena = bpy.data.scenes.new(h.slug)
        escena.world = mundo
        escena.collection.children.link(h.coleccion)
        escena.collection.children.link(luz)
        mn, mx = h.limites()
        camara(f"Cámara {h.slug}", iso, (mn + mx) / 2, escena)
        configurar_render(escena, 1200, 900, os.path.join(IMAGENES, h.slug + ".png"))

    # Portada: la suite en formato ancho, corrida a la derecha para dejar lugar al título
    # y un poco hacia arriba, porque la barra de búsqueda flota sobre el borde inferior
    suite = habitaciones[-1]
    portada = bpy.data.scenes.new("portada")
    portada.world = mundo
    portada.collection.children.link(suite.coleccion)
    portada.collection.children.link(luz)
    ancha = bpy.data.cameras.new("Cámara portada")
    ancha.type = "ORTHO"
    ancha.ortho_scale = alto_p * 1.3 * 1920 / 900
    ancha.shift_x = -0.16
    ancha.shift_y = -0.012
    ancha.clip_end = 100
    mn, mx = suite.limites()
    camara("Cámara portada", ancha, (mn + mx) / 2, portada)
    configurar_render(portada, 1920, 900, os.path.join(IMAGENES, "hero.png"))

    # Resumen: las cuatro en fila, de la más chica a la más grande
    resumen.world = mundo
    resumen.collection.children.link(luz)
    x = 0.0
    for h in habitaciones:
        x += h.ancho / 2
        inst = bpy.data.objects.new(h.titulo, None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = h.coleccion
        inst.location = (x, 0, 0)
        resumen.collection.objects.link(inst)
        x += h.ancho / 2 + 1.5
    vista = bpy.data.cameras.new("Cámara resumen")
    vista.type = "ORTHO"
    vista.ortho_scale = x * 0.85
    vista.clip_end = 200
    camara("Cámara resumen", vista, Vector(((x - 1.5) / 2, 0, 1)), resumen)
    configurar_render(resumen, 1920, 1080, "")
    return habitaciones


# ---------------------------------------------------------------- entregables

def renderizar(escenas=("simple", "doble-estandar", "doble-superior", "suite-mirador", "portada")):
    os.makedirs(IMAGENES, exist_ok=True)
    for nombre in escenas:
        bpy.ops.render.render(write_still=True, scene=nombre)


def exportar(slugs=("simple", "doble-estandar", "doble-superior", "suite-mirador")):
    """Exporta cada habitación a .glb con las transformaciones aplicadas: copia los objetos,
    les aplica la matriz a la malla y exporta solo esas copias (sin cámaras ni luces)."""
    os.makedirs(MODELOS, exist_ok=True)
    escena = bpy.context.window.scene
    for slug in slugs:
        coleccion = bpy.data.scenes[slug].collection.children[0]
        temporal = bpy.data.collections.new("_exportar")
        escena.collection.children.link(temporal)
        for o in coleccion.objects:
            malla = o.data.copy()
            malla.transform(o.matrix_basis)
            if o.matrix_basis.determinant() < 0:
                malla.flip_normals()
            copia = bpy.data.objects.new(o.name, malla)
            temporal.objects.link(copia)
        for o in escena.objects:
            o.select_set(o.name in temporal.objects)
        bpy.ops.export_scene.gltf(
            filepath=os.path.join(MODELOS, slug + ".glb"), export_format="GLB",
            use_selection=True, export_cameras=False, export_lights=False,
            export_apply=True, export_texcoords=False, export_yup=True)
        for o in list(temporal.objects):
            malla = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(malla)
        bpy.data.collections.remove(temporal)


def guardar():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    armar()
