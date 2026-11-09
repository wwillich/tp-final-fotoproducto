"""
Configuración de los tests.

Redirige la carpeta de almacenamiento a un directorio temporal ANTES de
importar la aplicación, para que los tests no toquen los datos reales.
"""

import os
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="fotoproducto-tests-"))
STORAGE_DIR = _TMP / "storage"
BACKEND_DIR = Path(__file__).resolve().parent.parent
os.environ["TP_STORAGE_DIR"] = str(STORAGE_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def foto_bytes(ancho: int, alto: int, formato: str = "PNG") -> bytes:
    """Foto sintética: mitad izquierda roja y mitad derecha azul (para ver qué parte se conserva)."""
    from io import BytesIO

    import numpy as np

    from fotoproducto import to_pil

    img = np.zeros((alto, ancho, 3), np.uint8)
    img[:, : ancho // 2] = (0, 0, 255)  # BGR: rojo
    img[:, ancho // 2:] = (255, 0, 0)   # BGR: azul
    buf = BytesIO()
    to_pil(img).save(buf, format=formato)
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)
