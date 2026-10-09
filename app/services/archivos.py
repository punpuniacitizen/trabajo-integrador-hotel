"""Archivos que sube el hotel desde Configuración: logo, portada, fotos y modelos 3D.

Se guardan en instance/uploads/ con un nombre nuevo (nunca el que trae el archivo) y se
sirven con la ruta /media/<nombre>. Además de la extensión se revisan los primeros bytes,
así un archivo cualquiera renombrado a .png no pasa.
"""
import os
import secrets

from flask import current_app

from app.services.errores import ErrorDeNegocio

# clase de archivo -> (extensiones, tamaño máximo en MB, cómo se describe en los mensajes)
CLASES = {
    "imagen": ({".png", ".jpg", ".jpeg", ".webp"}, 8, "una imagen PNG, JPG o WebP"),
    "logo": ({".png", ".jpg", ".jpeg", ".webp", ".svg"}, 2, "una imagen PNG, JPG, WebP o SVG"),
    "modelo": ({".glb"}, 20, "un modelo 3D en formato .glb"),
}


def _contenido_valido(extension, inicio):
    if extension == ".png":
        return inicio.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in (".jpg", ".jpeg"):
        return inicio.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP"
    if extension == ".glb":
        return inicio[:4] == b"glTF"
    if extension == ".svg":
        return b"<svg" in inicio.lower()
    return False


def carpeta():
    return os.path.join(current_app.instance_path, "uploads")


def guardar(archivo, clase, prefijo):
    """Guarda un archivo de request.files. Devuelve el nombre guardado, o None si no se eligió ninguno."""
    if not archivo or not archivo.filename:
        return None
    extensiones, maximo_mb, descripcion = CLASES[clase]
    extension = os.path.splitext(archivo.filename)[1].lower()
    datos = archivo.read()
    if extension not in extensiones or not _contenido_valido(extension, datos[:2048]):
        raise ErrorDeNegocio(f"«{archivo.filename}» no es {descripcion}.")
    if len(datos) > maximo_mb * 1024 * 1024:
        raise ErrorDeNegocio(f"«{archivo.filename}» pesa más de {maximo_mb} MB.")

    nombre = f"{prefijo}-{secrets.token_hex(4)}{extension}"
    with open(os.path.join(carpeta(), nombre), "wb") as destino:
        destino.write(datos)
    return nombre


def borrar(nombre):
    if not nombre:
        return
    ruta = os.path.join(carpeta(), os.path.basename(nombre))
    if os.path.isfile(ruta):
        os.remove(ruta)
