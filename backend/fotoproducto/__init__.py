"""
fotoproducto: núcleo de procesamiento de fotos de productos.

Deja una foto casera lista para publicar en una tienda online o red social.
NO debe importar FastAPI ni nada de `app`, para poder usarse desde la API, desde
la línea de comandos (`python -m fotoproducto`) o desde cualquier otro programa.
"""

from fotoproducto.exceptions import ErrorFotoProducto, InvalidImage
from fotoproducto.imageio import Photo, encode_png, from_pil, read_photo, to_pil

__all__ = [
    "ErrorFotoProducto", "InvalidImage", "Photo",
    "encode_png", "from_pil", "read_photo", "to_pil",
]
