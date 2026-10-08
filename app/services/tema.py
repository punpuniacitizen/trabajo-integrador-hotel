"""Colores del tema del hotel.

Cada hotel elige su color de acento. El texto que va encima (botones principales,
avatares) se elige solo entre blanco y casi negro para que siempre se lea bien.
Es la misma cuenta que hace el brandbook (design/identidad/brandbook.html).
"""
import re

TINTA = "#18181B"
BLANCO = "#FFFFFF"

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def es_color_valido(color):
    return bool(color and _HEX.fullmatch(color))


def _luminancia(color):
    canales = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(color_a, color_b):
    claro, oscuro = sorted((_luminancia(color_a), _luminancia(color_b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def texto_sobre(color_acento):
    """Blanco o casi negro: el que tenga más contraste con el color de acento."""
    if contraste(color_acento, BLANCO) >= contraste(color_acento, TINTA):
        return BLANCO
    return TINTA
