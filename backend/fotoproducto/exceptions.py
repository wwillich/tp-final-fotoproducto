"""
Excepciones de dominio del core.

El core solo lanza estas excepciones: no sabe nada de HTTP. Quien lo usa decide
cómo informarlas (la API con un código de estado, la línea de comandos con un
mensaje por stderr).
"""


class ErrorFotoProducto(Exception):
    """Clase base de todos los errores del core."""


class InvalidImage(ErrorFotoProducto):
    """Los bytes no se pueden abrir como imagen (vacío, dañado, no es una imagen)."""


class PlataformaDesconocida(ErrorFotoProducto):
    """La clave de plataforma pedida no está en el catálogo."""


class MarcasInsuficientes(ErrorFotoProducto):
    """Falta marcar el producto, el fondo, o las dos cosas."""


class ProductoNoEncontrado(ErrorFotoProducto):
    """Con las marcas dadas la separación dejó una máscara vacía o casi vacía."""
