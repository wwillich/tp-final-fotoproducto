"""Tests de la base del proyecto (F0)."""

import subprocess
import sys
from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image

from conftest import BACKEND_DIR
from fotoproducto import InvalidImage, read_photo, to_pil


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_frontend_servido(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Tu foto" in r.text


def test_el_frontend_se_revalida_en_cada_carga(client):
    for ruta in ("/", "/app.js", "/styles.css"):
        assert client.get(ruta).headers["cache-control"] == "no-cache"
    assert "cache-control" not in client.get("/api/health").headers


def test_core_no_importa_la_web():
    """Importar fotoproducto no debe cargar fastapi, starlette ni app."""
    code = (
        "import sys, fotoproducto;"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('fastapi', 'starlette', 'app')];"
        "sys.exit(1 if bad else 0)"
    )
    assert subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR).returncode == 0


def test_read_photo_detecta_formato_y_devuelve_bgr():
    img = np.zeros((20, 30, 3), np.uint8)
    img[:, :, 2] = 255  # rojo en BGR
    buf = BytesIO()
    to_pil(img).save(buf, format="PNG")
    foto = read_photo(buf.getvalue())
    assert foto.format == "PNG"
    assert (foto.width, foto.height) == (30, 20)
    assert foto.image[0, 0].tolist() == [0, 0, 255]


def test_read_photo_aplica_orientacion_exif():
    pil = Image.new("RGB", (30, 20), "white")
    exif = Image.Exif()
    exif[0x0112] = 6  # hay que rotar 90° para verla derecha
    buf = BytesIO()
    pil.save(buf, format="JPEG", exif=exif)
    foto = read_photo(buf.getvalue())
    assert (foto.width, foto.height) == (20, 30)


def test_read_photo_rechaza_basura():
    with pytest.raises(InvalidImage):
        read_photo(b"esto no es una imagen")
