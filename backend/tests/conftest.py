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


def png_bytes(imagen) -> bytes:
    """Codifica una imagen BGR como PNG."""
    from io import BytesIO

    from fotoproducto import to_pil

    buf = BytesIO()
    to_pil(imagen).save(buf, format="PNG")
    return buf.getvalue()


def escena(lado: int = 200):
    """Producto de prueba: cuadrado azul-rojizo (60..140) sobre un fondo gris."""
    import numpy as np

    img = np.full((lado, lado, 3), 200, np.uint8)
    img[60:140, 60:140] = (30, 60, 200)
    return img


def escena_ruidosa(lado: int = 200, caja: tuple[int, int, int, int] = (60, 140, 60, 140)):
    """Como escena(), pero con ruido de color: grabCut necesita variación para ajustar sus modelos.

    `caja` = (y0, y1, x0, x1) del producto.
    """
    import numpy as np

    azar = np.random.default_rng(0)
    y0, y1, x0, x1 = caja
    img = np.full((lado, lado, 3), 200, np.int16)
    img[y0:y1, x0:x1] = (30, 60, 200)
    return np.clip(img + azar.integers(-10, 11, img.shape), 0, 255).astype(np.uint8)


def contorno(lado: int = 200, caja: tuple[int, int, int, int] = (50, 150, 50, 150)):
    """Contorno de prueba: zona blanca (algo más grande que el producto) sobre negro."""
    import numpy as np

    img = np.zeros((lado, lado, 3), np.uint8)
    y0, y1, x0, x1 = caja
    img[y0:y1, x0:x1] = 255
    return img


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)
