"""Configuración del hotel (solo rol administración): datos del hotel, habitaciones y usuarios."""
import re
from itertools import groupby

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.auth import admin_requerido
from app.extensions import db
from app.models import Habitacion, TipoHabitacion, Usuario
from app.services import archivos, configuracion
from app.services import hotel as hotel_servicio
from app.services.errores import ErrorDeNegocio
from app.services.tema import es_color_valido

bp = Blueprint("configuracion", __name__, url_prefix="/administracion/configuracion")
bp.before_request(admin_requerido)

HORA = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def _texto(campo):
    return request.form.get(campo, "").strip()


def _lista(campo):
    """Textarea de "una por línea": saca las líneas vacías y los espacios de más."""
    lineas = [linea.strip() for linea in request.form.get(campo, "").splitlines() if linea.strip()]
    return "\n".join(lineas) or None


def _entero(campo):
    try:
        return int(request.form.get(campo, ""))
    except ValueError:
        return None


def _guardar_archivos(pedidos):
    """pedidos: [(campo del formulario, clase, prefijo)]. Si uno falla, borra los que ya se guardaron."""
    guardados = {}
    try:
        for campo, clase, prefijo in pedidos:
            guardados[campo] = archivos.guardar(request.files.get(campo), clase, prefijo)
    except ErrorDeNegocio:
        for nombre in guardados.values():
            archivos.borrar(nombre)
        raise
    return guardados


def _reemplazar(objeto, atributo, nuevo, quitar, viejos):
    """Pone el archivo nuevo (o lo saca si se tildó "quitar") y anota el anterior para borrarlo."""
    if nuevo or quitar:
        viejos.append(getattr(objeto, atributo))
        setattr(objeto, atributo, nuevo)


# --- Hotel -------------------------------------------------------------------------------

@bp.route("/", methods=["GET", "POST"])
def hotel():
    config = g.hotel
    if request.method == "POST":
        nombre, color = _texto("nombre"), _texto("color_acento").upper()
        checkin, checkout = _texto("hora_checkin"), _texto("hora_checkout")
        moneda = _texto("moneda") or "$"
        try:
            if not nombre:
                raise ErrorDeNegocio("Poné el nombre del hotel.")
            if not es_color_valido(color):
                raise ErrorDeNegocio("El color tiene que ser un código como #1F6F5C.")
            if not (HORA.fullmatch(checkin) and HORA.fullmatch(checkout)):
                raise ErrorDeNegocio("Los horarios tienen que tener el formato 14:00.")
            if len(moneda) > 8:
                raise ErrorDeNegocio("El símbolo de la moneda puede tener hasta 8 caracteres.")
            coordenadas = hotel_servicio.parsear_coordenadas(_texto("coordenadas"))
            email = hotel_servicio.normalizar_email(_texto("email"))
            whatsapp = hotel_servicio.normalizar_whatsapp(_texto("whatsapp"))
            instagram = hotel_servicio.normalizar_instagram(_texto("instagram"))
            nuevos = _guardar_archivos([("logo", "logo", "logo"), ("portada", "imagen", "portada")])
        except ErrorDeNegocio as error:
            flash(str(error), "danger")
            return render_template("configuracion/hotel.html", seccion="hotel", datos=request.form), 422

        viejos = []
        config.nombre = nombre
        config.eslogan = _texto("eslogan") or None
        config.ciudad = _texto("ciudad") or None
        config.color_acento = color
        config.hora_checkin, config.hora_checkout, config.moneda = checkin, checkout, moneda
        config.presentacion = request.form.get("presentacion", "").strip() or None
        config.servicios = _lista("servicios")
        config.informacion = _lista("informacion")
        config.direccion = _texto("direccion") or None
        config.latitud, config.longitud = coordenadas or (None, None)
        config.telefono = _texto("telefono") or None
        config.email, config.whatsapp, config.instagram = email, whatsapp, instagram
        _reemplazar(config, "logo", nuevos["logo"], "quitar_logo" in request.form, viejos)
        _reemplazar(config, "portada", nuevos["portada"], "quitar_portada" in request.form, viejos)
        if config.id is None:
            db.session.add(config)
        db.session.commit()
        for nombre_archivo in viejos:
            archivos.borrar(nombre_archivo)
        flash("Configuración del hotel guardada.", "success")
        return redirect(url_for(".hotel"))

    return render_template("configuracion/hotel.html", seccion="hotel", datos=None)


# --- Tipos de habitación -----------------------------------------------------------------

def _tipos():
    return db.session.scalars(db.select(TipoHabitacion).order_by(TipoHabitacion.tarifa_base)).all()


def _guardar_tipo(tipo):
    """Valida el formulario, guarda los archivos y actualiza el tipo. Devuelve los archivos viejos."""
    nombre = " ".join(_texto("nombre").split())
    capacidad, tarifa, metros = _entero("capacidad"), _entero("tarifa"), _entero("metros")
    configuracion.validar_tipo(nombre, capacidad, tarifa, metros, excluir=tipo if tipo.id else None)
    slug = tipo.slug or configuracion.slug_unico(nombre)
    nuevos = _guardar_archivos([("imagen", "imagen", f"tipo-{slug}"), ("modelo", "modelo", f"tipo-{slug}")])

    viejos = []
    tipo.nombre, tipo.slug = nombre, slug
    tipo.capacidad, tipo.tarifa_base, tipo.metros = capacidad, tarifa, metros
    tipo.descripcion = _texto("descripcion") or None
    comodidades = [linea.strip() for linea in _texto("comodidades").splitlines() if linea.strip()]
    tipo.comodidades = "\n".join(comodidades) or None
    _reemplazar(tipo, "imagen", nuevos["imagen"], "quitar_imagen" in request.form, viejos)
    _reemplazar(tipo, "modelo", nuevos["modelo"], "quitar_modelo" in request.form, viejos)
    return viejos


@bp.route("/tipos/nuevo", methods=["GET", "POST"], endpoint="tipo_nuevo")
@bp.route("/tipos/<int:tipo_id>", methods=["GET", "POST"])
def tipo(tipo_id=None):
    tipo = db.get_or_404(TipoHabitacion, tipo_id) if tipo_id else TipoHabitacion()
    if request.method == "POST":
        try:
            viejos = _guardar_tipo(tipo)
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("configuracion/tipo.html", seccion="habitaciones", tipo=tipo,
                                   datos=request.form), 422
        if tipo.id is None:
            db.session.add(tipo)
        db.session.commit()
        for nombre_archivo in viejos:
            archivos.borrar(nombre_archivo)
        flash(f"Tipo «{tipo.nombre}» guardado.", "success")
        return redirect(url_for(".habitaciones") + "#tipos")

    return render_template("configuracion/tipo.html", seccion="habitaciones", tipo=tipo, datos=None)


@bp.post("/tipos/<int:tipo_id>/eliminar")
def eliminar_tipo(tipo_id):
    tipo = db.get_or_404(TipoHabitacion, tipo_id)
    archivos_del_tipo = [tipo.imagen, tipo.modelo]
    try:
        configuracion.eliminar_tipo(tipo)
    except ErrorDeNegocio as error:
        flash(str(error), "danger")
        return redirect(url_for(".tipo", tipo_id=tipo.id))
    db.session.commit()
    for nombre_archivo in archivos_del_tipo:
        archivos.borrar(nombre_archivo)
    flash(f"Tipo «{tipo.nombre}» eliminado.", "success")
    return redirect(url_for(".habitaciones") + "#tipos")


# --- Pisos y habitaciones -----------------------------------------------------------------

@bp.get("/habitaciones")
def habitaciones():
    habitaciones = db.session.scalars(db.select(Habitacion).order_by(Habitacion.piso, Habitacion.numero)).all()
    pisos = [(piso, list(grupo)) for piso, grupo in groupby(habitaciones, key=lambda h: h.piso)]
    ultimo_piso = pisos[-1][0] if pisos else 0
    return render_template(
        "configuracion/habitaciones.html",
        seccion="habitaciones",
        tipos=_tipos(),
        pisos=pisos,
        piso_sugerido=ultimo_piso or 1,
        siguiente_piso=ultimo_piso + 1,
    )


@bp.post("/habitaciones/agregar")
def agregar_habitaciones():
    tipo = db.session.get(TipoHabitacion, _entero("tipo_id") or 0)
    piso = _entero("piso")
    try:
        nuevas = configuracion.agregar_habitaciones(piso, _entero("cantidad"), tipo, _entero("desde"))
    except ErrorDeNegocio as error:
        flash(str(error), "danger")
        return redirect(url_for(".habitaciones") + "#pisos")
    db.session.commit()
    rango = nuevas[0].numero if len(nuevas) == 1 else f"{nuevas[0].numero} a {nuevas[-1].numero}"
    texto = "Se agregó la habitación" if len(nuevas) == 1 else f"Se agregaron {len(nuevas)} habitaciones:"
    flash(f"{texto} {rango} ({tipo.nombre}).", "success")
    return redirect(url_for(".habitaciones") + f"#piso-{piso}")


@bp.post("/habitaciones/<int:habitacion_id>/tipo")
def cambiar_tipo(habitacion_id):
    habitacion = db.get_or_404(Habitacion, habitacion_id)
    tipo = db.get_or_404(TipoHabitacion, _entero("tipo_id") or 0)
    try:
        configuracion.cambiar_tipo(habitacion, tipo)
    except ErrorDeNegocio as error:
        flash(str(error), "danger")
    else:
        db.session.commit()
        flash(f"La {habitacion.numero} ahora es {tipo.nombre}.", "success")
    return redirect(url_for(".habitaciones") + f"#piso-{habitacion.piso}")


@bp.post("/habitaciones/<int:habitacion_id>/eliminar")
def eliminar_habitacion(habitacion_id):
    habitacion = db.get_or_404(Habitacion, habitacion_id)
    piso, numero = habitacion.piso, habitacion.numero
    try:
        configuracion.eliminar_habitacion(habitacion)
    except ErrorDeNegocio as error:
        flash(str(error), "danger")
    else:
        db.session.commit()
        flash(f"Habitación {numero} eliminada.", "success")
    return redirect(url_for(".habitaciones") + f"#piso-{piso}")


# --- Usuarios ----------------------------------------------------------------------------

@bp.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    datos = None
    if request.method == "POST":
        try:
            usuario = configuracion.crear_usuario(
                _texto("nombre"), _texto("email"), _texto("rol"), request.form.get("password", "")
            )
        except ErrorDeNegocio as error:
            flash(str(error), "danger")
            datos = request.form
        else:
            db.session.commit()
            flash(f"Usuario de {usuario.nombre} creado.", "success")
            return redirect(url_for(".usuarios"))

    lista = db.session.scalars(db.select(Usuario).order_by(Usuario.rol, Usuario.nombre)).all()
    return render_template("configuracion/usuarios.html", seccion="usuarios", usuarios=lista,
                           datos=datos), 422 if datos else 200


@bp.post("/usuarios/<int:usuario_id>/eliminar")
def eliminar_usuario(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    try:
        configuracion.eliminar_usuario(usuario, g.usuario)
    except ErrorDeNegocio as error:
        flash(str(error), "danger")
    else:
        db.session.commit()
        flash(f"Usuario de {usuario.nombre} eliminado.", "success")
    return redirect(url_for(".usuarios"))
