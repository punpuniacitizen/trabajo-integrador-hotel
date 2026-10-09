class ErrorDeNegocio(Exception):
    """Una operación que no se puede hacer. El mensaje se le muestra tal cual al usuario."""


class RequiereConfirmacion(ErrorDeNegocio):
    """Se puede hacer, pero el usuario tiene que confirmarlo (el mensaje es la pregunta)."""
