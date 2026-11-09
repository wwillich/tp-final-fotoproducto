"""
fotoproducto: núcleo de procesamiento de fotos de productos.

Deja una foto casera lista para publicar en una tienda online o red social.
NO debe importar FastAPI ni nada de `app`, para poder usarse desde la API, desde
la línea de comandos (`python -m fotoproducto`) o desde cualquier otro programa.
"""

from fotoproducto.editor import EditorFotoProducto, OpcionesEdicion, ResultadoEdicion
from fotoproducto.exceptions import (
    ErrorFotoProducto, InvalidImage, MarcasInsuficientes, PlataformaDesconocida, ProductoNoEncontrado,
)
from fotoproducto.imageio import Photo, encode_png, from_pil, read_photo, to_pil
from fotoproducto.plataformas import CatalogoPlataformas, Plataforma

__all__ = [
    "CatalogoPlataformas", "EditorFotoProducto", "ErrorFotoProducto", "InvalidImage",
    "MarcasInsuficientes", "OpcionesEdicion", "Photo", "Plataforma", "PlataformaDesconocida",
    "ProductoNoEncontrado", "ResultadoEdicion", "encode_png", "from_pil", "read_photo", "to_pil",
]
