"""
Entrada/salida de imágenes y conversión Pillow ↔ OpenCV (base del TP2).

Todo el core trabaja con imágenes de OpenCV: arrays de NumPy de forma
(alto, ancho, 3) en orden BGR y dtype uint8, o (alto, ancho) para un solo canal.
Este módulo es el único que convierte desde y hacia Pillow.
"""

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from fotoproducto.exceptions import InvalidImage


@dataclass(frozen=True)
class Photo:
    """A photo ready to be processed."""

    format: str        # "PNG", "JPEG", "WEBP", "BMP", "GIF"… detected by content
    image: np.ndarray  # BGR, already rotated according to its EXIF orientation

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]


def read_photo(content: bytes) -> Photo:
    """
    Opens the bytes of a photo with Pillow.

    - The format is detected by content, not by the file name.
    - The EXIF orientation is applied: phones store the pixels rotated and write
      in the EXIF how to display them. After this, (0, 0) is the top-left corner
      of the photo as it is seen on screen.
    - Any color mode (P, RGBA, L, CMYK…) is converted to RGB and then to BGR.

    Raises InvalidImage if the bytes are not an image. It does not filter
    formats: that is up to the caller.
    """
    try:
        with Image.open(BytesIO(content)) as img:
            img.load()
            fmt = img.format or ""
            upright = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidImage("El archivo no es una imagen válida o está dañado.") from exc
    return Photo(format=fmt, image=from_pil(upright))


def from_pil(img: Image.Image) -> np.ndarray:
    """Pillow image (any mode) → BGR array."""
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def to_pil(image: np.ndarray) -> Image.Image:
    """BGR array → Pillow RGB image; single channel array → Pillow L image."""
    if image.ndim == 2:
        return Image.fromarray(image, "L")
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), "RGB")


def encode_png(image: np.ndarray) -> bytes:
    """
    Encodes the image as PNG, in memory. A BGR array is saved as RGB and a
    single channel array as grayscale (mode L).
    """
    buf = BytesIO()
    to_pil(image).save(buf, format="PNG")
    return buf.getvalue()
