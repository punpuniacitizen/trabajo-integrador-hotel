"""Arma en Blender las cuatro habitaciones de docs/modelos-3d.md y renderiza sus imágenes.

Se corre dentro de Blender (por ejemplo, desde el MCP de Blender):

    ruta = r"...\\design\\3d\\armar_habitaciones.py"
    g = {"__file__": ruta, "__name__": "__main__"}
    exec(open(ruta, encoding="utf-8").read(), g)   # borra el archivo abierto y arma todo
    g["guardar"]()

Los renders y el horneado tardan, así que conviene hacerlos en segundo plano, con el .blend
ya guardado:

    blender -b design/3d/habitaciones.blend --python design/3d/armar_habitaciones.py -- renderizar gpu
    blender -b design/3d/habitaciones.blend --python design/3d/armar_habitaciones.py -- hornear gpu

renderizar genera los PNG; hornear genera los .glb del visor 3D con la luz horneada en una
textura. "gpu" usa la placa de video si hay; sin eso trabaja con el procesador.
"""
import math
import os
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KIT = os.path.join(RAIZ, "design", "3d", "kenney-furniture")
BLEND = os.path.join(RAIZ, "design", "3d", "habitaciones.blend")
IMAGENES = os.path.join(RAIZ, "app", "static", "img", "habitaciones")
MODELOS = os.path.join(RAIZ, "app", "static", "modelos")

ESCALA = 0.175          # unidades de Kenney -> metros (la bedDouble queda en 1,67 x 1,97 m)
PARED_KENNEY = 0.0875   # espesor de las paredes del kit, ya en metros
TRAMO = 1.75            # largo de un tramo de pared del kit (wall, wallWindow...)
ALTO_PARED = 12.9 * ESCALA
ESPESOR = 0.14          # espesor de las paredes del diorama
LOSA = 0.18             # espesor de la losa del piso
VENTANAL = 2.0          # cuánto se ensancha wallWindowSlide (una ventana guillotina chica)
MARCO = 0.66            # ancho del marco de wallWindow; el ventanal lo multiplica por VENTANAL
SEPARACION = 0.06       # entre la pared y los muebles, para dejar lugar a la boiserie
ALTO_BOISERIE = 0.72
COLCHON = 0.44          # altura de la frazada de las camas del kit

# ---------------------------------------------------------------- paleta (hex sRGB)

PARED = "EFE3CF"
BOISERIE = "2F6655"
BORDE = "1F6F5C"
TELAS = {
    "lino": "F4EEE4", "avena": "E2D2B6", "crema": "EADCC3", "terracota": "C0643F",
    "terracota_oscura": "8E4A30", "mostaza": "D39A3A", "salvia": "8FA586", "verde": "2F5F4F",
    "cortina": "EDE2CF", "peluche": "A5754C",
}
LIENZO = {
    "papel": "F3EBDD", "cielo": "F2D3B0", "sol": "E5A447", "monte_lejano": "93A6A2",
    "monte": "5F7F78", "nieve": "F7F2EA", "lago": "7FA9B3", "bosque": "4E6E55",
    "arco_1": "C0643F", "arco_2": "D39A3A", "arco_3": "8FA586", "arena": "E2CDAE",
}
# Materiales del kit de Kenney -> materiales propios
KENNEY = {
    "wood": "roble", "woodDark": "nogal", "carpet": "terracota", "carpetDarker": "terracota_oscura",
    "carpetWhite": "lino", "_defaultMat": "crema_mueble", "metal": "laton", "metalDark": "grafito",
    "metalLight": "ceramica", "metalMedium": "metal_gris", "glass": "vidrio", "lamp": "pantalla",
    "plant": "planta", "fur": "peluche",
}

ROT_CAMARA = (math.radians(54.7356), 0.0, math.radians(45.0))
HACIA_CAMARA = Vector((1.0, -1.0, 1.0)).normalized()
HACIA_SOL = Vector((-0.8, 0.35, 0.45)).normalized()   # sol de tarde: entra por las ventanas


# ---------------------------------------------------------------- materiales

def lineal(hex_color):
    """'EDE7DE' -> (r, g, b, 1) en espacio lineal."""
    def canal(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (canal(hex_color[0:2]), canal(hex_color[2:4]), canal(hex_color[4:6]), 1.0)


def tono(hex_color, k):
    r, g, b, _ = lineal(hex_color)
    return (min(r * (1 + k), 1), min(g * (1 + k), 1), min(b * (1 + k), 1), 1.0)


def nuevo(nombre, hex_vista="CCCCCC"):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    m.diffuse_color = lineal(hex_vista)
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


def principled(nt, salida, rugosidad=0.6, **entradas):
    """Principled BSDF; las entradas se pasan con guion bajo en vez de espacio (Base_Color)."""
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], salida.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = rugosidad
    for nombre, valor in entradas.items():
        bsdf.inputs[nombre.replace("_", " ")].default_value = valor
    return bsdf


def coordenadas(nt, espacio="Object", escala=(1, 1, 1), rotacion=(0, 0, 0)):
    """Vector de coordenadas: 'Object' (local al objeto) o 'Position' (del mundo)."""
    if espacio == "Position":
        vector = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    else:
        vector = nt.nodes.new("ShaderNodeTexCoord").outputs[espacio]
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Scale"].default_value = escala
    mapeo.inputs["Rotation"].default_value = rotacion
    nt.links.new(vector, mapeo.inputs["Vector"])
    return mapeo.outputs["Vector"]


def manchado(nt, vector, hex_color, cantidad, escala, detalle=3.0):
    """Color con variaciones suaves (ruido) alrededor de hex_color."""
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = escala
    ruido.inputs["Detail"].default_value = detalle
    nt.links.new(vector, ruido.inputs["Vector"])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].position = 0.3
    rampa.color_ramp.elements[1].position = 0.7
    rampa.color_ramp.elements[0].color = tono(hex_color, -cantidad)
    rampa.color_ramp.elements[1].color = tono(hex_color, cantidad)
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    return rampa.outputs["Color"], ruido


def relieve(nt, bsdf, altura, fuerza, distancia=0.002, invertir=False):
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = fuerza
    bump.inputs["Distance"].default_value = distancia
    bump.invert = invertir
    nt.links.new(altura, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def liso(nombre, hex_color, rugosidad=0.6, variacion=0.04, escala=6.0, espacio="Object", **extra):
    m, nt, salida = nuevo(nombre, hex_color)
    bsdf = principled(nt, salida, rugosidad, **extra)
    color, _ = manchado(nt, coordenadas(nt, espacio), hex_color, variacion, escala)
    nt.links.new(color, bsdf.inputs["Base Color"])
    return m


def tela(nombre, hex_color):
    m, nt, salida = nuevo(nombre, hex_color)
    bsdf = principled(nt, salida, 0.9, Sheen_Weight=0.4, Sheen_Roughness=0.4, Specular_IOR_Level=0.2)
    color, _ = manchado(nt, coordenadas(nt), hex_color, 0.07, 9.0, 4.0)
    nt.links.new(color, bsdf.inputs["Base Color"])
    return m


def madera(nombre, hex_color):
    m, nt, salida = nuevo(nombre, hex_color)
    bsdf = principled(nt, salida, 0.45, Specular_IOR_Level=0.4)
    color, ruido = manchado(nt, coordenadas(nt, escala=(1.2, 28, 1.2)), hex_color, 0.16, 2.5, 7.0)
    nt.links.new(color, bsdf.inputs["Base Color"])
    relieve(nt, bsdf, ruido.outputs["Fac"], 0.08)
    return m


def yeso(nombre, hex_color):
    m, nt, salida = nuevo(nombre, hex_color)
    bsdf = principled(nt, salida, 0.9, Specular_IOR_Level=0.15)
    vector = coordenadas(nt, "Position")
    color, _ = manchado(nt, vector, hex_color, 0.035, 1.6, 4.0)
    nt.links.new(color, bsdf.inputs["Base Color"])
    grano = nt.nodes.new("ShaderNodeTexNoise")
    grano.inputs["Scale"].default_value = 45
    grano.inputs["Detail"].default_value = 8
    nt.links.new(vector, grano.inputs["Vector"])
    relieve(nt, bsdf, grano.outputs["Fac"], 0.06)
    return m


def tablas(nombre, claro, oscuro, junta, ancho, largo, espacio="Position", rotacion=(0, 0, 0),
           rugosidad=0.4, veta=True):
    """Tablas, azulejos o machimbre: textura de ladrillos con dos tonos y juntas hundidas."""
    m, nt, salida = nuevo(nombre, claro)
    bsdf = principled(nt, salida, rugosidad, Specular_IOR_Level=0.35)
    ladrillo = nt.nodes.new("ShaderNodeTexBrick")
    ladrillo.offset = 0.37
    ladrillo.offset_frequency = 1
    ladrillo.inputs["Scale"].default_value = 1.0
    ladrillo.inputs["Brick Width"].default_value = largo
    ladrillo.inputs["Row Height"].default_value = ancho
    ladrillo.inputs["Mortar Size"].default_value = 0.004
    ladrillo.inputs["Mortar Smooth"].default_value = 0.3
    ladrillo.inputs["Mortar"].default_value = lineal(junta)
    nt.links.new(coordenadas(nt, espacio, rotacion=rotacion), ladrillo.inputs["Vector"])
    if veta:
        vetas = coordenadas(nt, espacio, escala=(0.5, 22, 1), rotacion=rotacion)
        for entrada, hex_color in (("Color1", claro), ("Color2", oscuro)):
            color, _ = manchado(nt, vetas, hex_color, 0.12, 2.0, 6.0)
            nt.links.new(color, ladrillo.inputs[entrada])
    else:
        ladrillo.inputs["Color1"].default_value = lineal(claro)
        ladrillo.inputs["Color2"].default_value = lineal(oscuro)
    nt.links.new(ladrillo.outputs["Color"], bsdf.inputs["Base Color"])
    relieve(nt, bsdf, ladrillo.outputs["Fac"], 0.5, invertir=True)
    return m


def ventana(nombre, para_hornear=False):
    """Vidrio de las ventanas: la cámara ve un cielo de tarde y la luz del sol pasa de largo.
    Para hornear, el cielo se ve desde cualquier rayo menos los de sombra."""
    m, nt, salida = nuevo(nombre, "F2DEC2")
    cielo = nt.nodes.new("ShaderNodeEmission")
    cielo.inputs["Strength"].default_value = 1.3
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].position = 0.36
    rampa.color_ramp.elements[0].color = lineal("F8D2A2")
    rampa.color_ramp.elements[1].position = 0.78
    rampa.color_ramp.elements[1].color = lineal("D4E4E8")
    separar = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], separar.inputs[0])
    nt.links.new(separar.outputs["Z"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], cielo.inputs["Color"])
    mezcla = nt.nodes.new("ShaderNodeMixShader")
    camino = nt.nodes.new("ShaderNodeLightPath")
    transparente = nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0]
    if para_hornear:
        nt.links.new(camino.outputs["Is Shadow Ray"], mezcla.inputs[0])
        nt.links.new(cielo.outputs[0], mezcla.inputs[1])
        nt.links.new(transparente, mezcla.inputs[2])
    else:
        nt.links.new(camino.outputs["Is Camera Ray"], mezcla.inputs[0])
        nt.links.new(transparente, mezcla.inputs[1])
        nt.links.new(cielo.outputs[0], mezcla.inputs[2])
    nt.links.new(mezcla.outputs[0], salida.inputs["Surface"])
    return m


def sin_luz(nombre, imagen):
    """Material que muestra una imagen tal cual. El exportador lo reconoce como
    KHR_materials_unlit (truco de Light Path + Emission)."""
    m, nt, salida = nuevo(nombre)
    textura = nt.nodes.new("ShaderNodeTexImage")
    textura.image = imagen
    emision = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(textura.outputs["Color"], emision.inputs["Color"])
    mezcla = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(nt.nodes.new("ShaderNodeLightPath").outputs["Is Camera Ray"], mezcla.inputs[0])
    nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], mezcla.inputs[1])
    nt.links.new(emision.outputs[0], mezcla.inputs[2])
    nt.links.new(mezcla.outputs[0], salida.inputs["Surface"])
    return m


def pantalla_lampara(nombre):
    m, nt, salida = nuevo(nombre, "FFE2B0")
    principled(nt, salida, 0.8, Base_Color=lineal("F4E6CC"), Emission_Color=lineal("FFC987"),
               Emission_Strength=5.0)
    return m


def cortina(nombre):
    """Lino que deja pasar algo de luz."""
    m, nt, salida = nuevo(nombre, TELAS["cortina"])
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Sheen Weight"].default_value = 0.3
    color, _ = manchado(nt, coordenadas(nt), TELAS["cortina"], 0.06, 7.0)
    nt.links.new(color, bsdf.inputs["Base Color"])
    luz = nt.nodes.new("ShaderNodeBsdfTranslucent")
    luz.inputs["Color"].default_value = lineal("F6D9AE")
    mezcla = nt.nodes.new("ShaderNodeMixShader")
    mezcla.inputs[0].default_value = 0.35
    nt.links.new(bsdf.outputs[0], mezcla.inputs[1])
    nt.links.new(luz.outputs[0], mezcla.inputs[2])
    nt.links.new(mezcla.outputs[0], salida.inputs["Surface"])
    return m


def plano(nombre, hex_color, rugosidad=0.9):
    m, nt, salida = nuevo(nombre, hex_color)
    principled(nt, salida, rugosidad, Base_Color=lineal(hex_color), Specular_IOR_Level=0.1)
    return m


FABRICAS = {
    "pared": lambda n: yeso(n, PARED),
    "boiserie": lambda n: tablas(n, BOISERIE, BOISERIE, "244F42", 5.0, 0.14, "Object",
                                 (math.radians(90), 0, 0), 0.45, veta=False),
    "boiserie_lisa": lambda n: liso(n, BOISERIE, 0.45, 0.02),
    "piso": lambda n: tablas(n, "C6A27C", "AE855E", "5E412A", 0.16, 1.2, rugosidad=0.5),
    "azulejo": lambda n: tablas(n, "E4E8DE", "D5DDD3", "BFC5BC", 0.15, 0.15, rugosidad=0.25, veta=False),
    "borde": lambda n: liso(n, BORDE, 0.7, 0.03),
    "techo": lambda n: plano(n, "F2EAD9"),
    "roble": lambda n: madera(n, "B7834F"),
    "nogal": lambda n: madera(n, "7B4F33"),
    "crema_mueble": lambda n: liso(n, "EADFCB", 0.5, 0.03),
    "laton": lambda n: liso(n, "C9A063", 0.3, 0.05, Metallic=1.0),
    "metal_gris": lambda n: liso(n, "8A8C88", 0.35, 0.03, Metallic=1.0),
    "grafito": lambda n: liso(n, "34393A", 0.5, 0.05),
    "ceramica": lambda n: liso(n, "F3EFE8", 0.12, 0.02),
    "espejo": lambda n: plano(n, "E8EEF0", 0.03),
    "vidrio": lambda n: liso(n, "DDEBEA", 0.05, 0.0, Transmission_Weight=1.0),
    "ventana": ventana,
    "ventana_horno": lambda n: ventana(n, para_hornear=True),
    "pantalla": pantalla_lampara,
    "pantalla_tv": lambda n: plano(n, "1E2324", 0.15),
    "planta": lambda n: liso(n, "4F8A5B", 0.55, 0.15, 12.0),
    "maceta": lambda n: liso(n, "B86A47", 0.7, 0.06),
    "maceta_oscura": lambda n: liso(n, "8E4E33", 0.7, 0.06),
    "cortina": cortina,
}
for _nombre, _hex in TELAS.items():
    FABRICAS.setdefault(_nombre, lambda n, h=_hex: tela(n, h))
for _nombre, _hex in LIENZO.items():
    FABRICAS["lienzo_" + _nombre] = lambda n, h=_hex: plano(n, h)


def material(nombre):
    return bpy.data.materials.get(nombre) or FABRICAS[nombre](nombre)


# ---------------------------------------------------------------- geometría propia

def malla(nombre, vertices, caras, materiales, indices=None):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vertices, [], caras)
    for m in materiales:
        me.materials.append(material(m))
    for cara, i in zip(me.polygons, indices or []):
        cara.material_index = i
    me.update()
    return me


class Piezas:
    """Junta cajas y polígonos en una sola malla con varios materiales."""

    def __init__(self):
        self.v, self.f, self.i, self.mats = [], [], [], []

    def _mat(self, nombre):
        if nombre not in self.mats:
            self.mats.append(nombre)
        return self.mats.index(nombre)

    def cara(self, puntos, mat):
        base = len(self.v)
        self.v += puntos
        self.f.append(tuple(range(base, base + len(puntos))))
        self.i.append(self._mat(mat))

    def caja(self, x0, x1, y0, y1, z0, z1, mat, mat_arriba=None):
        base = len(self.v)
        self.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for k, c in enumerate(((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6),
                               (3, 0, 4, 7))):
            self.f.append(tuple(base + j for j in c))
            self.i.append(self._mat(mat_arriba if k == 1 and mat_arriba else mat))

    def malla(self, nombre):
        return malla(nombre, self.v, self.f, self.mats, self.i)


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
    """Importa un OBJ del kit una sola vez y deja la malla en metros, Z arriba, apoyada en z = 0
    y centrada en planta (los tramos de pared, centrados en su espesor). Los materiales del kit
    se cambian por los propios; los nombres originales quedan en malla["kenney"]."""
    if nombre in _kit:
        return _kit[nombre]
    antes = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(KIT, nombre + ".obj"),
                          mtl_name_collision_mode="REFERENCE_EXISTING")
    obj = next(o for o in bpy.data.objects if o not in antes)
    me = obj.data
    me.transform(Matrix.Scale(ESCALA, 4) @ obj.matrix_basis)
    bpy.data.objects.remove(obj)

    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    centro_y = PARED_KENNEY / 2 if nombre.startswith("wall") else -(min(ys) + max(ys)) / 2
    me.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, centro_y, -min(zs))))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    me.name = "kit_" + nombre

    originales = [m.name.split(".")[0] if m else "" for m in me.materials]
    me["kenney"] = originales
    for i, original in enumerate(originales):
        propio = KENNEY.get(original, "crema_mueble")
        if nombre.startswith("wall"):
            propio = {"metalDark": "pared", "_defaultMat": "pared", "glass": "ventana"}.get(original, propio)
        me.materials[i] = material(propio)
    _kit[nombre] = me
    return me


def con_telas(me, telas):
    """Copia de una malla del kit con algunos materiales cambiados ({nombre en Kenney: propio})."""
    copia = me.copy()
    for i, original in enumerate(me["kenney"]):
        if original in telas:
            copia.materials[i] = material(telas[original])
    return copia


# ---------------------------------------------------------------- habitaciones

class Habitacion:
    """Diorama de ancho x fondo (medidas interiores, en metros) centrado en el origen.
    La pared del fondo está en +Y y la de la izquierda en -X; el frente (-Y) y la derecha (+X)
    quedan abiertos."""

    def __init__(self, slug, titulo, ancho, fondo):
        self.slug, self.titulo, self.ancho, self.fondo = slug, titulo, ancho, fondo
        self.coleccion = bpy.data.collections.new(titulo)
        self.losa()
        self.techo()

    # -- ubicación

    def objeto(self, nombre, me, ubicacion, rot=0.0, escala=(1, 1, 1)):
        obj = bpy.data.objects.new(nombre, me)
        obj.location = ubicacion
        obj.rotation_euler = (0, 0, math.radians(rot))
        obj.scale = escala
        self.coleccion.objects.link(obj)
        return obj

    def mueble(self, nombre, x, y, rot=0.0, z=0.0, escala=1.0, telas=None, inclinar=0.0):
        """Coloca un mueble del kit. rot = 0 mira a +Y, 180 a -Y (a la cámara),
        -90 a +X y 90 a -X. telas cambia materiales: {nombre en Kenney: material propio}."""
        me = cargar(nombre)
        if telas:
            me = con_telas(me, telas)
        if isinstance(escala, (int, float)):
            escala = (escala,) * 3
        obj = self.objeto(nombre, me, (x, y, z), rot, escala)
        obj.rotation_euler.x = math.radians(inclinar)  # XYZ: primero se inclina y después se gira
        return obj

    def sobre_pared(self, pared, a_lo_largo, distancia):
        """Punto en planta a cierta distancia de la cara interior de una pared."""
        if pared == "fondo":
            return a_lo_largo, self.fondo / 2 - distancia
        return -self.ancho / 2 + distancia, a_lo_largo

    def contra_pared(self, nombre, pared, a_lo_largo, separacion=SEPARACION, **kw):
        """Mueble con la espalda contra la pared del fondo o la de la izquierda.
        a_lo_largo es la coordenada sobre la pared (x en el fondo, y en la izquierda)."""
        esc = kw.get("escala", 1.0)
        esc_y = esc if isinstance(esc, (int, float)) else esc[1]
        prof = max(v.co.y for v in cargar(nombre).vertices) * 2 * esc_y
        x, y = self.sobre_pared(pared, a_lo_largo, separacion + prof / 2)
        return self.mueble(nombre, x, y, rot=180 if pared == "fondo" else -90, **kw)

    def en_pared(self, nombre, pared, a_lo_largo, me):
        """Objeto armado en coordenadas de pared: X a lo largo, Z arriba y -Y hacia la habitación."""
        x, y = self.sobre_pared(pared, a_lo_largo, 0.0)
        return self.objeto(nombre, me, (x, y, 0), 0 if pared == "fondo" else 90)

    def lampara(self, nombre, x, y, z=0.0, rot=0.0, potencia=30.0, **kw):
        """Lámpara del kit encendida: la pantalla brilla y adentro hay una luz puntual."""
        obj = self.mueble(nombre, x, y, rot, z, **kw)
        obj.visible_shadow = False
        me = obj.data
        pantalla = {i for i, m in enumerate(me.materials) if m and m.name == "pantalla"}
        puntos = [me.vertices[v].co for p in me.polygons if p.material_index in pantalla for v in p.vertices]
        luz = bpy.data.lights.new(f"Luz {nombre}", "POINT")
        luz.energy = potencia
        luz.shadow_soft_size = 0.05
        luz.color = (1.0, 0.72, 0.45)
        foco = bpy.data.objects.new(f"Luz {nombre}", luz)
        foco.location = obj.matrix_basis @ (sum(puntos, Vector()) / len(puntos))
        self.coleccion.objects.link(foco)
        return obj

    # -- estructura

    def losa(self):
        a, f = self.ancho, self.fondo
        p = Piezas()
        p.caja(-a / 2 - ESPESOR, a / 2, -f / 2, f / 2 + ESPESOR, -LOSA, 0, "borde", mat_arriba="piso")
        self.objeto("Losa", p.malla(f"losa_{self.slug}"), (0, 0, 0))

    def techo(self):
        """Techo que la cámara no ve: hace que el sol entre solo por las ventanas."""
        a, f = self.ancho, self.fondo
        x0, x1, y0, y1 = -a / 2 - ESPESOR, a / 2, -f / 2, f / 2 + ESPESOR
        me = malla(f"techo_{self.slug}", [(x0, y0, 0), (x0, y1, 0), (x1, y1, 0), (x1, y0, 0)],
                   [(0, 1, 2, 3)], ["techo"])
        obj = self.objeto("Techo", me, (0, 0, ALTO_PARED + 0.005))
        obj.visible_camera = False
        obj.visible_glossy = False
        obj.visible_transmission = False

    def pared(self, lado, aberturas=()):
        """Arma la pared del fondo o la de la izquierda con tramos del kit y le agrega boiserie.
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
        for centro, pieza, ensanche in sorted(aberturas) + [(None, None, None)]:
            hasta = fin if centro is None else centro - TRAMO * ensanche / 2
            if hasta - cursor > 0.01:
                largo = hasta - cursor
                self.objeto(f"Pared {lado}", cargar("wall"), ubicar(cursor + largo / 2), rot,
                            (largo / TRAMO, grosor, 1))
            if centro is None:
                break
            self.objeto(f"{pieza} {lado}", cargar(pieza), ubicar(centro), rot, (ensanche, grosor, 1))
            cursor = centro + TRAMO * ensanche / 2
        self.boiserie(lado)

    def boiserie(self, lado):
        """Machimbre pintado de verde hasta media altura, con zócalo y moldura."""
        if lado == "fondo":
            u0, u1 = -self.ancho / 2, self.ancho / 2
        else:
            u0, u1 = -self.fondo / 2, self.fondo / 2 - 0.045
        largo, h = u1 - u0, ALTO_BOISERIE
        p = Piezas()
        p.caja(-largo / 2, largo / 2, -0.025, 0, 0, h, "boiserie")
        p.caja(-largo / 2, largo / 2, -0.045, 0, h, h + 0.04, "boiserie_lisa")
        p.caja(-largo / 2, largo / 2, -0.04, 0, 0, 0.1, "boiserie_lisa")
        self.en_pared(f"Boiserie {lado}", lado, (u0 + u1) / 2, p.malla(f"boiserie_{self.slug}_{lado}"))

    def tabique(self, x0, y0, x1, y1, alto=1.1, espesor=0.1):
        """Media pared interior (wallHalf estirado), cortada a media altura para que se vea adentro."""
        largo = math.hypot(x1 - x0, y1 - y0)
        rot = math.degrees(math.atan2(y1 - y0, x1 - x0))
        self.objeto("Tabique", cargar("wallHalf"), ((x0 + x1) / 2, (y0 + y1) / 2, 0), rot,
                    (largo / (TRAMO / 2), espesor / PARED_KENNEY, alto / ALTO_PARED))

    def parche(self, nombre, x0, y0, x1, y1, mat):
        """Rectángulo apenas por encima del piso (por ejemplo, el piso del baño)."""
        me = malla(nombre, [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [(0, 1, 2, 3)], [mat])
        return self.objeto(nombre, me, (0, 0, 0.004))

    # -- textiles y decoración

    def cortinas(self, lado, centro, ensanche=1.0, abajo=0.03, arriba=2.1):
        """Dos paños de lino plisados a los costados de la ventana, con su barral."""
        marco = MARCO * ensanche
        ancho_pano, onda, alto_onda, columnas = 0.34, 0.085, 0.035, 28
        p = Piezas()
        for u0 in (marco / 2 - 0.04, -(marco / 2 - 0.04) - ancho_pano):
            puntos = []
            for k in range(columnas + 1):
                u = u0 + ancho_pano * k / columnas
                puntos.append((u, -0.07 - alto_onda * (0.5 + 0.5 * math.sin(2 * math.pi * u / onda))))
            for (ua, da), (ub, db) in zip(puntos, puntos[1:]):
                p.cara([(ua, da, abajo), (ub, db, abajo), (ub, db, arriba), (ua, da, arriba)], "cortina")
        extremo = marco / 2 + ancho_pano + 0.08
        p.caja(-extremo, extremo, -0.105, -0.085, arriba + 0.02, arriba + 0.04, "laton")
        for signo in (-1, 1):
            p.caja(signo * extremo - 0.025, signo * extremo + 0.025, -0.12, -0.07, arriba + 0.005,
                   arriba + 0.055, "laton")
        self.en_pared(f"Cortinas {lado}", lado, centro, p.malla(f"cortinas_{self.slug}_{lado}"))

    def cuadro(self, lado, centro, z, ancho, alto, estilo="montanas"):
        """Cuadro enmarcado con una ilustración plana: 'montanas' (cerros y lago) o 'arcos'."""
        p = Piezas()
        p.caja(-ancho / 2, ancho / 2, -0.03, 0, z, z + alto, "nogal")
        b = 0.035
        p.cara([(-ancho / 2 + b, -0.031, z + b), (ancho / 2 - b, -0.031, z + b),
                (ancho / 2 - b, -0.031, z + alto - b), (-ancho / 2 + b, -0.031, z + alto - b)], "lienzo_papel")
        margen = 0.075
        aw, ah = ancho - 2 * margen, alto - 2 * margen
        aspecto = ah / aw

        def poligono(puntos, mat, capa):
            # puntos en fracciones del dibujo; cada capa un pelito más adelante que la anterior
            p.cara([(-aw / 2 + fx * aw, -0.032 - 0.0006 * capa, z + margen + fz * ah) for fx, fz in puntos], mat)

        def circulo(cx, cz, r, mat, capa, n=20):
            for k in range(n):
                a1, a2 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                poligono([(cx, cz), (cx + r * aspecto * math.cos(a1), cz + r * math.sin(a1)),
                          (cx + r * aspecto * math.cos(a2), cz + r * math.sin(a2))], mat, capa)

        if estilo == "montanas":
            poligono([(0, 0), (1, 0), (1, 1), (0, 1)], "lienzo_cielo", 0)
            circulo(0.72, 0.72, 0.13, "lienzo_sol", 1)
            for (a, b_, c), cima, mat, capa in (((0.0, 0.62, 0.3), 0.82, "lienzo_monte_lejano", 2),
                                               ((0.35, 1.0, 0.68), 0.66, "lienzo_monte", 3)):
                poligono([(a, 0.25), (b_, 0.25), (c, cima)], mat, capa)
                f = 0.22
                poligono([(c + (a - c) * f, cima - (cima - 0.25) * f), (c + (b_ - c) * f, cima - (cima - 0.25) * f),
                          (c, cima)], "lienzo_nieve", capa + 2)
            poligono([(0, 0.12), (1, 0.12), (1, 0.25), (0, 0.25)], "lienzo_lago", 6)
            poligono([(0, 0), (1, 0), (1, 0.12), (0, 0.12)], "lienzo_bosque", 6)
        else:
            poligono([(0, 0), (1, 0), (1, 1), (0, 1)], "lienzo_papel", 0)
            poligono([(0, 0), (1, 0), (1, 0.14), (0, 0.14)], "lienzo_arena", 1)
            for k, mat in enumerate(("lienzo_arco_3", "lienzo_arco_2", "lienzo_arco_1")):
                r0, r1, n = 0.14 + 0.13 * k, 0.26 + 0.13 * k, 16
                for j in range(n):
                    a1, a2 = math.pi * j / n, math.pi * (j + 1) / n
                    poligono([(0.5 + r0 * aspecto * math.cos(a1), 0.14 + r0 * math.sin(a1)),
                              (0.5 + r1 * aspecto * math.cos(a1), 0.14 + r1 * math.sin(a1)),
                              (0.5 + r1 * aspecto * math.cos(a2), 0.14 + r1 * math.sin(a2)),
                              (0.5 + r0 * aspecto * math.cos(a2), 0.14 + r0 * math.sin(a2))], mat, 2)
            circulo(0.82, 0.8, 0.08, "lienzo_arco_1", 3)
        self.en_pared(f"Cuadro {estilo}", lado, centro, p.malla(f"cuadro_{self.slug}_{lado}_{centro}"))

    def repisa(self, lado, centro, z, largo, cosas=()):
        """Estante de nogal amurado; cosas = [(modelo, desplazamiento, telas)]."""
        p = Piezas()
        p.caja(-largo / 2, largo / 2, -0.2, 0, z - 0.03, z, "nogal")
        self.en_pared("Repisa", lado, centro, p.malla(f"repisa_{self.slug}_{lado}_{centro}"))
        for modelo, desplazamiento, telas in cosas:
            self.contra_pared(modelo, lado, centro + desplazamiento, separacion=0.03, z=z, telas=telas)

    def cama(self, modelo, x, y, frazada, manta, almohadones=()):
        """Cama contra la pared del fondo (mira a -Y), con manta a los pies y almohadones."""
        ancho = 1.67 if modelo == "bedDouble" else 1.0
        self.mueble(modelo, x, y, rot=180, telas={"carpet": frazada})
        pie = y - 0.985
        p = Piezas()
        x0, x1, y0, y1 = x - ancho / 2 - 0.035, x + ancho / 2 + 0.035, pie + 0.14, pie + 0.6
        p.caja(x0, x1, y0, y1, COLCHON, COLCHON + 0.035, manta)
        p.caja(x0, x0 + 0.025, y0, y1, COLCHON - 0.2, COLCHON + 0.035, manta)
        p.caja(x1 - 0.025, x1, y0, y1, COLCHON - 0.2, COLCHON + 0.035, manta)
        self.objeto("Manta", p.malla(f"manta_{self.slug}"), (0, 0, 0))
        n = len(almohadones)
        for k, (modelo_almohadon, tela_) in enumerate(almohadones):
            dx = (k - (n - 1) / 2) * 0.46
            self.mueble(modelo_almohadon, x + dx, y + 0.6, rot=180, z=COLCHON, inclinar=15,
                        telas={"carpet": tela_})

    def mesas_de_luz(self, cama_x, ancho_cama, lampara, potencia=30.0):
        for lado in (-1, 1):
            x = cama_x + lado * (ancho_cama / 2 + 0.06 + 0.235)
            self.contra_pared("cabinetBedDrawerTable", "fondo", x)
            _, y = self.sobre_pared("fondo", x, SEPARACION + 0.15)
            self.lampara(lampara, x - lado * 0.06, y, z=0.46, rot=180, potencia=potencia)

    def banco(self, cama_x, cama_y, tela_, ancho=1.7):
        self.mueble("benchCushionLow", cama_x, cama_y - 0.985 - 0.27, escala=(ancho, 1, 1),
                    telas={"carpet": tela_})

    def limites(self):
        """Caja que envuelve lo que ve la cámara (para encuadrarla)."""
        puntos = []
        for o in self.coleccion.objects:
            if o.type == "MESH" and o.visible_camera:
                puntos += [o.matrix_basis @ Vector(c) for c in o.bound_box]
        mn = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
        mx = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
        return mn, mx


ALFOMBRA = {"carpet": "crema", "carpetDarker": "terracota"}
LIBROS = {"carpetDarker": "terracota", "carpetWhite": "crema", "plant": "salvia", "metal": "mostaza"}
MACETA = {"wood": "maceta", "woodDark": "maceta_oscura"}
PANTALLA = {"metal": "pantalla_tv"}


def simple():
    h = Habitacion("simple", "Simple", 3.0, 3.6)
    h.pared("fondo")
    h.pared("izquierda", [(-0.95, "wallWindow", 1.0)])
    h.cortinas("izquierda", -0.95, abajo=0.74)

    cama_x, cama_y = -1.5 + SEPARACION + 0.5, 1.8 - SEPARACION - 0.985
    h.cama("bedSingle", cama_x, cama_y, "avena", "terracota", [("pillow", "verde")])
    h.cuadro("fondo", cama_x, 1.12, 0.5, 0.4, "montanas")
    h.contra_pared("cabinetBedDrawerTable", "fondo", -0.15)
    h.lampara("lampRoundTable", -0.2, 1.55, z=0.46, rot=180, potencia=35)

    h.contra_pared("desk", "fondo", 0.8)
    h.mueble("chairCushion", 0.72, 1.02, rot=8, escala=1.25, telas={"carpet": "terracota"})
    h.contra_pared("laptop", "fondo", 0.62, separacion=0.2, z=0.67)
    h.contra_pared("books", "fondo", 1.2, separacion=0.1, z=0.67, telas=LIBROS)
    h.repisa("fondo", 0.8, 1.42, 0.9, [("books", -0.2, LIBROS), ("plantSmall2", 0.25, MACETA)])

    h.contra_pared("bookcaseOpenLow", "izquierda", -0.95)
    h.contra_pared("books", "izquierda", -1.1, separacion=0.12, z=0.7, telas=LIBROS)
    h.contra_pared("plantSmall1", "izquierda", -0.72, separacion=0.14, z=0.7, telas=MACETA)
    h.mueble("pottedPlant", -1.12, -1.6, rot=-30, telas=MACETA)
    h.mueble("rugRound", 0.35, -0.5, escala=0.9, telas=ALFOMBRA)
    return h


def doble_estandar():
    h = Habitacion("doble-estandar", "Doble estándar", 3.6, 4.2)
    h.pared("fondo")
    h.pared("izquierda", [(0.55, "wallWindow", 1.0)])
    h.cortinas("izquierda", 0.55)

    cama_x, cama_y = -0.25, 2.1 - SEPARACION - 0.985
    h.cama("bedDouble", cama_x, cama_y, "verde", "mostaza", [("pillow", "terracota"), ("pillow", "crema")])
    h.mesas_de_luz(cama_x, 1.67, "lampSquareTable")
    h.cuadro("fondo", cama_x - 0.32, 1.08, 0.46, 0.58, "montanas")
    h.cuadro("fondo", cama_x + 0.32, 1.08, 0.46, 0.58, "arcos")
    h.banco(cama_x, cama_y, "terracota")

    h.contra_pared("cabinetTelevision", "izquierda", -1.25)
    h.contra_pared("televisionModern", "izquierda", -1.25, separacion=0.12, z=0.54, telas=PANTALLA)
    h.mueble("coatRackStanding", 1.42, 1.72)
    h.mueble("rugRectangle", cama_x, -0.75, escala=0.8, telas=ALFOMBRA)
    h.mueble("pottedPlant", 1.45, -1.75, rot=20, telas=MACETA)
    return h


def doble_superior():
    h = Habitacion("doble-superior", "Doble superior", 4.2, 4.8)
    h.pared("fondo")
    h.pared("izquierda", [(0.1, "wallWindowSlide", VENTANAL)])
    h.cortinas("izquierda", 0.1, VENTANAL)

    cama_x, cama_y = -0.45, 2.4 - SEPARACION - 0.985
    h.cama("bedDouble", cama_x, cama_y, "avena", "verde",
           [("pillow", "mostaza"), ("pillow", "salvia"), ("pillow", "terracota")])
    h.mesas_de_luz(cama_x, 1.67, "lampRoundTable")
    h.cuadro("fondo", cama_x, 1.08, 1.0, 0.6, "montanas")
    h.banco(cama_x, cama_y, "verde", 1.8)

    # Rincón de lectura
    h.mueble("rugRound", 1.35, 1.25, escala=0.75, telas={"carpet": "salvia", "carpetDarker": "crema"})
    h.mueble("loungeChair", 1.35, 1.3, rot=145, telas={"carpet": "terracota"})
    h.lampara("lampRoundFloor", 1.88, 2.12, rot=200, potencia=45)
    h.contra_pared("pottedPlant", "izquierda", 1.62, telas=MACETA)

    # Escritorio bajo una repisa
    h.contra_pared("desk", "izquierda", -1.75)
    h.mueble("chairCushion", -1.3, -1.75, rot=95, escala=1.25, telas={"carpet": "verde"})
    h.lampara("lampSquareTable", -1.88, -2.22, z=0.67, rot=-90, potencia=25)
    h.contra_pared("laptop", "izquierda", -1.65, separacion=0.22, z=0.67)
    h.repisa("izquierda", -1.75, 1.42, 0.9, [("books", -0.18, LIBROS), ("plantSmall3", 0.25, MACETA)])

    h.mueble("rugRounded", -0.3, -0.8, escala=0.85, telas=ALFOMBRA)
    return h


def suite_mirador():
    h = Habitacion("suite-mirador", "Suite Mirador", 6.0, 5.0)
    h.pared("fondo", [(0.75, "wallWindowSlide", VENTANAL)])
    h.pared("izquierda", [(-0.75, "wallWindowSlide", VENTANAL)])
    h.cortinas("fondo", 0.75, VENTANAL, abajo=0.74)
    h.cortinas("izquierda", -0.75, VENTANAL, abajo=0.84)

    # Baño en el rincón del fondo a la izquierda, con tabiques a media altura
    h.parche("Piso baño", -3.0, 0.6, -0.8, 2.5, "azulejo")
    h.tabique(-0.8, 0.55, -0.8, 2.5)
    h.tabique(-3.0, 0.6, -1.85, 0.6)
    h.contra_pared("bathtub", "izquierda", 1.56, escala=0.85)
    h.contra_pared("bathroomSink", "fondo", -1.45)
    h.contra_pared("bathroomMirror", "fondo", -1.45, z=1.12, separacion=0.0, telas={"metal": "espejo"})

    # Dormitorio
    cama_x, cama_y = 0.75, 2.5 - SEPARACION - 0.985
    h.cama("bedDouble", cama_x, cama_y, "lino", "terracota",
           [("pillow", "verde"), ("pillowLong", "mostaza"), ("pillow", "verde")])
    h.mesas_de_luz(cama_x, 1.67, "lampSquareTable")
    h.banco(cama_x, cama_y, "verde", 1.8)
    h.mueble("pottedPlant", 2.62, 2.15, telas=MACETA)

    # Living (el sillón recto deja lugar a la mesa ratona)
    h.mueble("rugRound", -1.75, -0.8, escala=1.15, telas=ALFOMBRA)
    h.contra_pared("loungeSofa", "izquierda", -0.75, telas={"carpet": "verde"})
    h.mueble("tableCoffee", -1.55, -0.95, rot=90)
    h.mueble("books", -1.6, -0.75, z=0.4, rot=80, telas=LIBROS)
    h.mueble("plantSmall1", -1.5, -1.3, z=0.4, telas=MACETA)
    h.mueble("loungeChair", -1.55, 0.12, rot=180, telas={"carpet": "mostaza"})
    h.lampara("lampRoundFloor", -2.72, -2.12, rot=40, potencia=45)
    h.mueble("pottedPlant", -2.72, 0.32, rot=60, telas=MACETA)

    # Mesita para desayunar
    h.mueble("tableRound", 1.9, -1.35, escala=(0.55, 0.55, 1.15))
    h.mueble("chairCushion", 1.38, -1.35, rot=-90, escala=1.25, telas={"carpet": "terracota"})
    h.mueble("chairCushion", 2.42, -1.35, rot=90, escala=1.25, telas={"carpet": "terracota"})
    h.mueble("plantSmall1", 1.9, -1.35, z=0.74, telas=MACETA)
    return h


HABITACIONES = [simple, doble_estandar, doble_superior, suite_mirador]


# ---------------------------------------------------------------- escenas, cámara y luz

def configurar_render(escena, ancho, alto, archivo):
    try:
        escena.render.engine = "CYCLES"
    except TypeError:
        pass
    r = escena.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = ancho, alto, 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.filepath = archivo
    c = escena.cycles
    c.samples = 192
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.015
    c.use_denoising = True
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 8, 4, 3
    c.transmission_bounces, c.transparent_max_bounces = 4, 12
    c.caustics_reflective = c.caustics_refractive = False
    c.filter_width = 1.3
    try:
        escena.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            escena.view_settings.look = look
            break
        except TypeError:
            pass
    escena.view_settings.exposure = 0.0


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


def iluminacion():
    """Sol de tarde que entra por las ventanas, cielo tibio y una luz de relleno del lado abierto."""
    mundo = bpy.data.worlds.get("Ambiente") or bpy.data.worlds.new("Ambiente")
    mundo.use_nodes = True
    fondo = next(n for n in mundo.node_tree.nodes if n.type == "BACKGROUND")
    fondo.inputs[0].default_value = lineal("F1E2CC")
    fondo.inputs[1].default_value = 0.4

    luz = bpy.data.collections.new("Iluminación")
    sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", "SUN"))
    sol.data.energy = 9.0
    sol.data.angle = math.radians(2.5)
    sol.data.color = (1.0, 0.78, 0.55)
    sol.rotation_euler = HACIA_SOL.to_track_quat("Z", "Y").to_euler()
    luz.objects.link(sol)

    relleno = bpy.data.objects.new("Relleno", bpy.data.lights.new("Relleno", "AREA"))
    relleno.data.shape = "SQUARE"
    relleno.data.size = 7.0
    relleno.data.energy = 450
    relleno.data.color = (0.9, 0.94, 1.0)
    relleno.location = Vector((1, -1, 0.45)).normalized() * 9 + Vector((0, 0, 1))
    relleno.rotation_euler = (Vector((0, 0, 0.8)) - relleno.location).to_track_quat("-Z", "Y").to_euler()
    luz.objects.link(relleno)
    return mundo, luz


def armar():
    resumen = limpiar()
    mundo, luz = iluminacion()
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
    bpy.data.orphans_purge(do_recursive=True)
    return habitaciones


# ---------------------------------------------------------------- entregables

ESCENAS = ("simple", "doble-estandar", "doble-superior", "suite-mirador", "portada")


def renderizar(escenas=ESCENAS, porcentaje=100, muestras=None, carpeta=None):
    """Renderiza las escenas a app/static/img/habitaciones (o a otra carpeta, para pruebas)."""
    os.makedirs(carpeta or IMAGENES, exist_ok=True)
    for nombre in escenas:
        escena = bpy.data.scenes[nombre]
        antes = (escena.render.resolution_percentage, escena.cycles.samples, escena.render.filepath)
        escena.render.resolution_percentage = porcentaje
        if muestras:
            escena.cycles.samples = muestras
        if carpeta:
            escena.render.filepath = os.path.join(carpeta, os.path.basename(antes[2]))
        bpy.ops.render.render(write_still=True, scene=nombre)
        escena.render.resolution_percentage, escena.cycles.samples, escena.render.filepath = antes


# ---------------------------------------------------------------- horneado para el visor 3D

SLUGS = ("simple", "doble-estandar", "doble-superior", "suite-mirador")
TEXEL = 240             # píxeles de textura por metro de superficie
METALES = ("laton", "metal_gris")


def _escena_temporal(nombre, modelo, objetos):
    """Escena aparte con los objetos dados, el mismo mundo y el mismo color de los renders."""
    escena = bpy.data.scenes.new(nombre)
    escena.world = modelo.world
    escena.render.engine = modelo.render.engine
    escena.cycles.device = modelo.cycles.device
    escena.view_settings.view_transform = modelo.view_settings.view_transform
    escena.view_settings.look = modelo.view_settings.look
    for o in objetos:
        escena.collection.objects.link(o)
    return escena


def _en_escena(escena, activos, edicion=False):
    """Contexto de una escena con esos objetos seleccionados. En segundo plano no hay ventana,
    así que el objeto activo y la selección se pasan explícitos."""
    capa = escena.view_layers[0]
    for o in escena.objects:
        o.select_set(o in activos, view_layer=capa)
    capa.objects.active = activos[0]
    contexto = dict(scene=escena, view_layer=capa, active_object=activos[0], object=activos[0],
                    selected_objects=activos, selected_editable_objects=activos)
    if edicion:
        contexto["edit_object"] = activos[0]
    return bpy.context.temp_override(**contexto)


def _fusionar(nombre, objetos):
    """Una sola malla en coordenadas del mundo con todos los objetos y sus materiales. Guarda
    las coordenadas locales y las "generated" de cada objeto como atributos, para que las
    texturas procedurales se vean igual que en los objetos sueltos."""
    vertices, caras, indices, materiales, locales, generadas = [], [], [], [], [], []
    for o in objetos:
        me, base = o.data, len(vertices)
        cos = [v.co.copy() for v in me.vertices]
        mn = [min(c[i] for c in cos) for i in range(3)]
        tam = [max(max(c[i] for c in cos) - mn[i], 1e-6) for i in range(3)]
        for c in cos:
            vertices.append(o.matrix_basis @ c)
            locales.append(tuple(c))
            generadas.append(tuple((c[i] - mn[i]) / tam[i] for i in range(3)))
        mapa = []
        for m in me.materials:
            m = material("ventana_horno") if m and m.name == "ventana" else m
            if m not in materiales:
                materiales.append(m)
            mapa.append(materiales.index(m))
        for p in me.polygons:
            caras.append([base + i for i in p.vertices])
            indices.append(mapa[p.material_index] if mapa else 0)
    fusion = bpy.data.meshes.new(nombre)
    fusion.from_pydata(vertices, [], caras)
    for m in materiales:
        fusion.materials.append(m)
    fusion.polygons.foreach_set("material_index", indices)
    for atributo, valores in (("local", locales), ("generado", generadas)):
        fusion.attributes.new(atributo, "FLOAT_VECTOR", "POINT").data.foreach_set(
            "vector", [x for v in valores for x in v])
    fusion.uv_layers.new(name="horneado")
    fusion.update()
    return bpy.data.objects.new(nombre, fusion)


def _coordenadas_por_atributo(materiales):
    """Mientras se hornea, las salidas Object y Generated de los materiales pasan a leer los
    atributos de la malla fusionada. Devuelve lo necesario para deshacerlo."""
    cambios = []
    for m in materiales:
        nt = m.node_tree
        for enlace in list(nt.links):
            salida = enlace.from_socket
            if enlace.from_node.type == "TEX_COORD" and salida.name in ("Object", "Generated"):
                atributo = nt.nodes.new("ShaderNodeAttribute")
                atributo.attribute_name = "local" if salida.name == "Object" else "generado"
                destino = enlace.to_socket
                nt.links.remove(enlace)
                nt.links.new(atributo.outputs["Vector"], destino)
                cambios.append((nt, atributo, salida, destino))
    return cambios


def hornear(slug, muestras=1024, lado=None):
    """Hornea toda la luz de una habitación (sol, lámparas, rebotes) en una textura y exporta
    app/static/modelos/<slug>.glb: una sola malla con un material sin luz que la muestra.
    Cycles hornea objeto por objeto (y rearma la escena para cada uno), así que primero se
    fusiona todo en dos mallas: la habitación y las lámparas, que no deben tapar su propia luz.
    Trabaja en una escena temporal; los objetos originales no se tocan."""
    escena = bpy.data.scenes[slug]
    habitacion = next(c for c in escena.collection.children if c.name != "Iluminación")
    visibles = [o for o in habitacion.objects if o.type == "MESH" and o.visible_camera]
    auxiliares = [o for o in habitacion.objects if o not in visibles] + list(escena.collection.children["Iluminación"].objects)

    copias = [_fusionar(f"_cuarto_{slug}", [o for o in visibles if o.visible_shadow]),
              _fusionar(f"_lamparas_{slug}", [o for o in visibles if not o.visible_shadow])]
    copias[1].visible_shadow = False
    area = sum(p.area for c in copias for p in c.data.polygons)
    lado = lado or min(4096, math.ceil(math.sqrt(area / 0.5) * TEXEL / 256) * 256)
    horno = _escena_temporal(f"_horno_{slug}", escena, copias + auxiliares)
    horno.cycles.samples = muestras
    print(f"Horneando {slug}: {lado} px, {muestras} muestras, dispositivo {horno.cycles.device}", flush=True)

    with _en_escena(horno, copias):
        bpy.ops.object.mode_set(mode="EDIT")
    with _en_escena(horno, copias, edicion=True):
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=6 / lado)
        bpy.ops.object.mode_set(mode="OBJECT")

    # Cada material escribe en la imagen; los metales se hornean como difusos (sin reflejos)
    imagen = bpy.data.images.new(f"horneado_{slug}", lado, lado, float_buffer=True)
    materiales = {m for c in copias for m in c.data.materials if m}
    nodos = []
    for m in materiales:
        nodo = m.node_tree.nodes.new("ShaderNodeTexImage")
        nodo.image = imagen
        m.node_tree.nodes.active = nodo
        nodos.append((m, nodo))
    cambios = _coordenadas_por_atributo(materiales)
    metales = [next(n for n in bpy.data.materials[m].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
               for m in METALES if m in bpy.data.materials]
    for bsdf in metales:
        bsdf.inputs["Metallic"].default_value = 0.0
    try:
        with _en_escena(horno, copias):
            bpy.ops.object.bake(type="COMBINED", pass_filter={"DIRECT", "INDIRECT", "DIFFUSE", "TRANSMISSION", "EMIT"},
                                margin=8, margin_type="EXTEND", use_clear=True, target="IMAGE_TEXTURES")
    finally:
        for bsdf in metales:
            bsdf.inputs["Metallic"].default_value = 1.0
        for nt, atributo, salida, destino in cambios:
            nt.nodes.remove(atributo)
            nt.links.new(salida, destino)
        for m, nodo in nodos:
            m.node_tree.nodes.remove(nodo)

    # La textura se guarda con el mismo AgX de los renders, así el visor la muestra tal cual
    ruta = os.path.join(tempfile.gettempdir(), "conserje_horneado", f"{slug}.png")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    horno.render.image_settings.file_format = "PNG"
    horno.render.image_settings.color_mode = "RGB"
    imagen.save_render(ruta, scene=horno)
    textura = bpy.data.images.load(ruta)

    # Malla final: las dos fusionadas juntas, con sus UVs y el material sin luz
    vertices, caras, uvs = [], [], []
    for c in copias:
        me, base = c.data, len(vertices)
        vertices += [c.matrix_basis @ v.co for v in me.vertices]
        capa_uv = me.uv_layers["horneado"].data
        for p in me.polygons:
            caras.append([base + i for i in p.vertices])
            uvs += [tuple(capa_uv[i].uv) for i in p.loop_indices]
    final = malla(f"horneado_{slug}", vertices, caras, [])
    final.uv_layers.new(name="horneado").data.foreach_set("uv", [x for uv in uvs for x in uv])
    final.materials.append(sin_luz(f"horneado_{slug}", textura))
    unido = bpy.data.objects.new(f"Horneado {slug}", final)
    # Las mallas intermedias se borran antes de exportar; si no, el exportador las incluye
    bpy.data.scenes.remove(horno)
    for c in copias:
        bpy.data.objects.remove(c)

    # El exportador se exporta desde la escena activa de verdad: si se le pasa una escena
    # temporal por contexto, Blender 5.1 se cae al evaluarla.
    actual, capa = bpy.context.scene, bpy.context.view_layer
    actual.collection.objects.link(unido)
    for o in capa.objects:
        o.select_set(o == unido)
    capa.objects.active = unido
    os.makedirs(MODELOS, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(MODELOS, slug + ".glb"), export_format="GLB", use_selection=True,
        export_cameras=False, export_lights=False, export_texcoords=True, export_normals=False,
        export_image_format="WEBP", export_image_quality=85, export_yup=True)
    actual.collection.objects.unlink(unido)

    bpy.data.objects.remove(unido)
    bpy.data.images.remove(textura)
    bpy.data.images.remove(imagen)
    bpy.data.orphans_purge(do_recursive=True)
    return lado


def usar_gpu():
    """Renderiza con la placa de video si hay. Pensado para el Blender en segundo plano:
    cambia las preferencias solo en memoria y no las guarda."""
    preferencias = bpy.context.preferences
    preferencias.use_preferences_save = False
    cycles = preferencias.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            cycles.compute_device_type = tipo
        except TypeError:
            continue
        cycles.get_devices()
        if any(d.type == tipo for d in cycles.devices):
            for d in cycles.devices:
                d.use = d.type == tipo
            for escena in bpy.data.scenes:
                escena.cycles.device = "GPU"
            return tipo
    return None


def guardar():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    # Opciones: renderizar, hornear, gpu, los slugs a hornear y muestras=N (por defecto, todos y 1024)
    argumentos = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "renderizar" in argumentos or "hornear" in argumentos:
        if "gpu" in argumentos:
            print("Con", usar_gpu() or "CPU")
        if "renderizar" in argumentos:
            renderizar()
        if "hornear" in argumentos:
            muestras = next((int(a.split("=")[1]) for a in argumentos if a.startswith("muestras=")), 1024)
            for slug in [a for a in argumentos if a in SLUGS] or SLUGS:
                print("Horneada", slug, "en", hornear(slug, muestras), "px")
    else:
        armar()
