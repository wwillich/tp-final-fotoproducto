"""
Configuración de la aplicación.

Los tests redirigen la carpeta de almacenamiento con la variable de entorno
TP_STORAGE_DIR, así que las rutas y los límites se leen siempre de acá.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# En Vercel el disco es de solo lectura: lo único escribible es /tmp (y se pierde entre invocaciones).
EN_VERCEL = bool(os.environ.get("VERCEL"))
STORAGE_POR_DEFECTO = Path("/tmp/storage") if EN_VERCEL else BASE_DIR / "storage"

# Carpeta donde se guardan los trabajos (original, resultado y metadatos).
STORAGE_DIR = Path(os.environ.get("TP_STORAGE_DIR", STORAGE_POR_DEFECTO))

# URL pública bajo la que se sirve STORAGE_DIR.
MEDIA_URL = "/media"

# Formatos de foto aceptados (se detectan por contenido, no por extensión).
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}

# Tamaño máximo de una foto subida.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
