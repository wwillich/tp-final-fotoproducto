"""Tests de los endpoints de F1: plataformas y vista previa."""

import json
from typing import get_args
from urllib.parse import unquote

import cv2
import numpy as np

from app.core import editor
from app.esquemas import Adaptacion, Peso
from conftest import contorno, escena_ruidosa, foto_bytes, png_bytes
from fotoproducto.encuadre import ADAPTADORES


def vista_previa(client, contenido: bytes, nombre="foto.png", contorno_png: bytes | None = None, **datos):
    files = {"archivo": (nombre, contenido, "image/png")}
    if contorno_png is not None:
        files["contorno"] = ("contorno.png", contorno_png, "image/png")
    return client.post("/api/vista-previa", files=files, data=datos)


def test_contrato_coincide_con_el_core():
    assert set(get_args(Adaptacion)) == set(ADAPTADORES)
    assert set(get_args(Peso)) == set(editor.compresor.perfiles)


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
    assert r.headers["x-calidad"] in {"excelente", "muy%20buena", "buena", "aceptable"}
    assert "más chica" in json.loads(unquote(r.headers["x-avisos"]))[0]


def test_vista_previa_webp_para_tienda_nube(client):
    r = vista_previa(client, foto_bytes(2000, 2000), plataforma="tiendanube", adaptacion="recortar", posicion_x="0", posicion_y="1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert json.loads(unquote(r.headers["x-avisos"])) == []


def decodificar(contenido: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)


def test_vista_previa_quitar_fondo_reemplaza_el_fondo_por_blanco(client):
    foto = png_bytes(escena_ruidosa())
    auto = vista_previa(client, foto, plataforma="mercadolibre", peso="maxima", quitar_fondo="true")
    guiado = vista_previa(client, foto, contorno_png=png_bytes(contorno()), plataforma="mercadolibre", peso="maxima")
    sin = vista_previa(client, foto, plataforma="mercadolibre", peso="maxima")
    assert auto.status_code == 200 and guiado.status_code == 200
    assert decodificar(auto.content)[10:60, 10:60].min() > 245
    assert decodificar(guiado.content)[10:60, 10:60].min() > 245   # un contorno implica quitar el fondo
    assert abs(int(decodificar(sin.content)[10:60, 10:60].mean()) - 200) < 5


def test_vista_previa_contorno_vacio_da_422(client):
    r = vista_previa(client, png_bytes(escena_ruidosa()), contorno_png=png_bytes(contorno(caja=(0, 0, 0, 0))),
                     plataforma="mercadolibre")
    assert r.status_code == 422
    assert r.json()["detail"] == {
        "code": "CONTORNO_INVALIDO",
        "message": "El contorno no encierra ninguna zona de la foto. Dibujalo de nuevo rodeando el producto.",
    }


def test_vista_previa_producto_no_encontrado_da_422(client, monkeypatch):
    monkeypatch.setattr(editor.quitador, "area_minima", 0.9)
    r = vista_previa(client, png_bytes(escena_ruidosa()), plataforma="mercadolibre", quitar_fondo="true")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "PRODUCTO_NO_ENCONTRADO"


def test_vista_previa_valida_el_archivo_de_contorno(client):
    r = vista_previa(client, png_bytes(escena_ruidosa()), contorno_png=b"no es una imagen", plataforma="mercadolibre")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_FILE"


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
