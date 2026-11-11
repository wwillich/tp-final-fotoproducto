"""
Lectura y validación de una foto subida.

Todo endpoint que recibe una foto la valida igual, en este orden:

1. supera config.MAX_UPLOAD_BYTES        → 413 FILE_TOO_LARGE
2. no se puede abrir como imagen         → 400 INVALID_FILE (InvalidImage, del core)
3. formato fuera de config.ALLOWED_FORMATS → 400 UNSUPPORTED_FORMAT
"""

from dataclasses import dataclass

from fastapi import UploadFile

from app.config import ALLOWED_FORMATS, MAX_UPLOAD_BYTES
from app.errors import ApiError
from fotoproducto import Photo, read_photo


@dataclass(frozen=True)
class Upload:
    """Una foto ya validada: el archivo recibido y la imagen lista para el core."""

    name: str       # nombre que mandó el usuario (nunca usarlo para nombrar un archivo en disco)
    content: bytes   # el archivo tal como se recibió
    photo: Photo     # formato + imagen BGR derecha, lista para el core


async def read_upload(file: UploadFile) -> Upload:
    """Lee y valida la foto subida; lanza ApiError si es muy grande o de un formato no soportado."""
    # Lee a lo sumo un byte más que el límite, para no cargar entero un archivo enorme.
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ApiError(413, "FILE_TOO_LARGE", f"La foto supera el máximo de {limit_mb} MB.")

    photo = read_photo(content)
    if photo.format not in ALLOWED_FORMATS:
        allowed = ", ".join(sorted(ALLOWED_FORMATS))
        raise ApiError(400, "UNSUPPORTED_FORMAT",
                       f"El formato {photo.format or 'desconocido'} no está soportado. Usá {allowed}.")
    return Upload(name=file.filename or "foto", content=content, photo=photo)
