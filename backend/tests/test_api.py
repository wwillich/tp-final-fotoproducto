"""Tests de los endpoints de F1: plataformas y vista previa."""

import json
from typing import get_args
from urllib.parse import unquote

import cv2
import numpy as np

from app.esquemas import Adaptacion
from conftest import foto_bytes
from fotoproducto.encuadre import ADAPTADORES


def vista_previa(client, contenido: bytes, nombre="foto.png", **datos):
    return client.post("/api/vista-previa", files={"archivo": (nombre, contenido, "image/png")}, data=datos)


def test_contrato_coincide_con_el_core():
    assert set(get_args(Adaptacion)) == set(ADAPTADORES)


def test_plataformas(client):
    r = client.get("/api/plataformas")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 5
    assert datos[0] == {"clave": "mercadolibre", "nombre": "Mercado Libre", "ancho": 1200, "alto": 1200, "formato": "JPEG"}


def test_vista_previa_devuelve_la_imagen_y_los_datos_en_headers(client):
    r = vista_previa(client, foto_bytes(800, 600), plataforma="mercadolibre")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    assert img.shape[:2] == (1200, 1200)
    assert r.headers["x-ancho"] == "1200" and r.headers["x-alto"] == "1200"
    assert int(r.headers["x-peso-bytes"]) == len(r.content)
    assert "más chica" in json.loads(unquote(r.headers["x-avisos"]))[0]


def test_vista_previa_webp_para_tienda_nube(client):
    r = vista_previa(client, foto_bytes(2000, 2000), plataforma="tiendanube", adaptacion="recortar", posicion_x="0", posicion_y="1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert json.loads(unquote(r.headers["x-avisos"])) == []


def test_vista_previa_no_guarda_nada(client):
    from app.config import STORAGE_DIR

    vista_previa(client, foto_bytes(100, 100), plataforma="mercadolibre")
    assert not any(STORAGE_DIR.iterdir())


def test_vista_previa_plataforma_desconocida(client):
    r = vista_previa(client, foto_bytes(100, 100), plataforma="nada")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PLATAFORMA_DESCONOCIDA"


def test_vista_previa_opcion_fuera_de_rango(client):
    assert vista_previa(client, foto_bytes(100, 100), plataforma="mercadolibre", adaptacion="otra").status_code == 422
    for campo in ("posicion_x", "posicion_y"):
        for valor in ("-0.1", "1.5", "abc"):
            r = vista_previa(client, foto_bytes(100, 100), plataforma="mercadolibre", **{campo: valor})
            assert r.status_code == 422


def test_vista_previa_valida_el_archivo(client):
    r = vista_previa(client, b"no es una imagen", plataforma="mercadolibre")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_FILE"
    r = client.post("/api/vista-previa", files={"archivo": ("f.gif", foto_bytes(10, 10, "GIF"), "image/gif")},
                    data={"plataforma": "mercadolibre"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "UNSUPPORTED_FORMAT"
