"""Filtros de Jinja para mostrar fechas, montos y nombres en castellano."""
from flask import g

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def fecha_larga(fecha):
    """martes, 14 de octubre"""
    return f"{DIAS[fecha.weekday()]}, {fecha.day} de {MESES[fecha.month - 1]}"


def dia_mes(fecha):
    """14 de octubre"""
    return f"{fecha.day} de {MESES[fecha.month - 1]}"


def fecha_corta(fecha):
    """14 oct"""
    return f"{fecha.day} {MESES[fecha.month - 1][:3]}"


def rango_fechas(entrada, salida):
    """12 al 16 oct · 28 sep al 2 oct"""
    if entrada.month == salida.month:
        return f"{entrada.day} al {fecha_corta(salida)}"
    return f"{fecha_corta(entrada)} al {fecha_corta(salida)}"


def moneda(valor):
    """$ 192.000 (con el símbolo que configuró el hotel)"""
    simbolo = getattr(g.get("hotel"), "moneda", None) or "$"
    return f"{simbolo} {valor:,.0f}".replace(",", ".")


def iniciales(texto):
    palabras = [p for p in (texto or "").split() if p[:1].isalpha()]
    return "".join(p[0] for p in palabras[:2]).upper() or "?"


def documento_oculto(documento):
    """···382: en pantalla alcanza con los últimos dígitos."""
    if not documento:
        return "—"
    return "···" + documento[-3:]


def registrar(app):
    for filtro in (fecha_larga, dia_mes, fecha_corta, moneda, iniciales, documento_oculto):
        app.add_template_filter(filtro)
    app.add_template_global(rango_fechas)
