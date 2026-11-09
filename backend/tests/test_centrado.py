"""Tests de centrar el producto (F4): Centrador, editor, API y línea de comandos."""

import cv2
import numpy as np
import pytest

from conftest import BACKEND_DIR, contorno, escena_ruidosa, png_bytes
from fotoproducto import EditorFotoProducto, OpcionesEdicion
from fotoproducto.encuadre import ESPACIOS, Centrador

PRODUCTO = (30, 60, 200)
CONTORNO_LATERAL = contorno(caja=(8, 72, 128, 192))  # rodea al producto de arriba a la derecha


def caja(mascara: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mascara)
    return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1


def foto_con_producto(alto=300, ancho=400, y0=20, x0=300, lado=60):
    """Foto blanca con un cuadrado de producto, y su máscara."""
    imagen = np.full((alto, ancho, 3), 255, np.uint8)
    mascara = np.zeros((alto, ancho), np.uint8)
    imagen[y0:y0 + lado, x0:x0 + lado] = PRODUCTO
    mascara[y0:y0 + lado, x0:x0 + lado] = 255
    return imagen, mascara


# --- Centrador -------------------------------------------------------------------------

def test_centra_el_producto_con_el_margen_pedido():
    imagen, mascara = foto_con_producto(y0=100, x0=150)  # lejos de los bordes
    out = Centrador(0.25).centrar(imagen, mascara)
    margen = round(0.25 * 60)                              # 15 px a cada lado
    assert out.shape[:2] == (60 + 2 * margen, 60 + 2 * margen)
    y0, y1, x0, x1 = caja((out == PRODUCTO).all(axis=2))
    assert (y0, x0) == (margen, margen) and (y1, x1) == (margen + 60, margen + 60)


def test_si_el_margen_se_sale_de_la_foto_se_completa_con_blanco_sin_cortar_el_producto():
    imagen, mascara = foto_con_producto(y0=0, x0=340)  # pegado al borde de arriba y de la derecha
    out = Centrador(0.5).centrar(imagen, mascara)
    assert out.shape[:2] == (120, 120)
    assert ((out == PRODUCTO).all(axis=2)).sum() == 60 * 60        # el producto está entero
    y0, y1, x0, x1 = caja((out == PRODUCTO).all(axis=2))
    assert (y0, x0) == (30, 30) and (y1, x1) == (90, 90)           # centrado igual
    assert (out[:30] == 255).all() and (out[:, 90:] == 255).all()  # lo que falta es blanco


def test_mas_espacio_da_una_foto_mas_grande():
    imagen, mascara = foto_con_producto(y0=100, x0=150)
    lados = [Centrador(ESPACIOS[e]).centrar(imagen, mascara).shape[0] for e in ("poco", "normal", "mucho")]
    assert lados == sorted(lados) and len(set(lados)) == 3


def test_mascara_vacia_deja_la_imagen_como_esta():
    imagen, _ = foto_con_producto()
    assert Centrador().centrar(imagen, np.zeros(imagen.shape[:2], np.uint8)) is imagen


# --- Editor ----------------------------------------------------------------------------

def decodificar(contenido: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)


def test_editor_centra_el_producto_en_el_resultado():
    escena = escena_ruidosa(caja=(10, 70, 130, 190))  # producto arriba a la derecha
    op = OpcionesEdicion("mercadolibre", peso="maxima", quitar_fondo=True, centrar=True, espacio="normal")
    out = decodificar(EditorFotoProducto().procesar(escena, op, CONTORNO_LATERAL).contenido)
    y0, y1, x0, x1 = caja((np.abs(out.astype(int) - PRODUCTO).sum(axis=2) < 60))
    assert abs((x0 + x1) / 2 - 600) < 25 and abs((y0 + y1) / 2 - 600) < 25   # centro de 1200×1200


def test_editor_sin_centrar_el_producto_queda_donde_estaba():
    escena = escena_ruidosa(caja=(10, 70, 130, 190))
    op = OpcionesEdicion("mercadolibre", peso="maxima", quitar_fondo=True)
    out = decodificar(EditorFotoProducto().procesar(escena, op, CONTORNO_LATERAL).contenido)
    _, _, x0, x1 = caja((np.abs(out.astype(int) - PRODUCTO).sum(axis=2) < 60))
    assert (x0 + x1) / 2 > 700


def test_editor_centra_sin_quitar_el_fondo_y_deja_el_fondo_original():
    escena = escena_ruidosa(caja=(10, 70, 130, 190))
    op = OpcionesEdicion("mercadolibre", peso="maxima", centrar=True)   # quitar_fondo = False
    out = decodificar(EditorFotoProducto().procesar(escena, op, CONTORNO_LATERAL).contenido)
    y0, y1, x0, x1 = caja((np.abs(out.astype(int) - PRODUCTO).sum(axis=2) < 60))
    assert abs((x0 + x1) / 2 - 600) < 25 and abs((y0 + y1) / 2 - 600) < 25
    # Alrededor del producto sigue estando el gris original (no se pasó a blanco).
    assert abs(int(out[y0 - 30, 600, 0]) - 200) < 15


def test_editor_centra_sin_contorno_detectando_el_producto_solo():
    op = OpcionesEdicion("mercadolibre", peso="maxima", centrar=True)
    out = decodificar(EditorFotoProducto().procesar(escena_ruidosa(), op).contenido)
    y0, y1, x0, x1 = caja((np.abs(out.astype(int) - PRODUCTO).sum(axis=2) < 60))
    assert abs((x0 + x1) / 2 - 600) < 25 and abs((y0 + y1) / 2 - 600) < 25


def test_editor_un_contorno_solo_sigue_quitando_el_fondo():
    op = OpcionesEdicion("mercadolibre", peso="maxima")  # ni quitar_fondo ni centrar
    out = decodificar(EditorFotoProducto().procesar(escena_ruidosa(), op, contorno()).contenido)
    assert out[10:60, 10:60].min() > 245


# --- API -------------------------------------------------------------------------------

def test_api_centrar(client):
    datos = {"plataforma": "mercadolibre", "peso": "maxima", "quitar_fondo": "true", "centrar": "true", "espacio": "mucho"}
    r = client.post("/api/vista-previa", data=datos, files={"archivo": ("f.png", png_bytes(escena_ruidosa()), "image/png")})
    assert r.status_code == 200


def test_api_centrar_sin_quitar_el_fondo(client):
    r = client.post("/api/vista-previa", data={"plataforma": "mercadolibre", "peso": "maxima", "centrar": "true"},
                    files={"archivo": ("f.png", png_bytes(escena_ruidosa()), "image/png")})
    assert r.status_code == 200
    assert abs(int(decodificar(r.content)[5, 5, 0]) - 200) < 15   # el fondo original se conserva


def test_api_espacio_invalido_da_422(client):
    r = client.post("/api/vista-previa", data={"plataforma": "mercadolibre", "espacio": "enorme"},
                    files={"archivo": ("f.png", png_bytes(escena_ruidosa()), "image/png")})
    assert r.status_code == 422


def test_el_contrato_de_espacio_coincide_con_el_core():
    from typing import get_args

    from app.esquemas import Espacio

    assert set(get_args(Espacio)) == set(ESPACIOS)


# --- Línea de comandos -----------------------------------------------------------------

def test_cli_centrar(tmp_path):
    import os
    import subprocess
    import sys

    entrada, salida = tmp_path / "in.png", tmp_path / "out.jpg"
    entrada.write_bytes(png_bytes(escena_ruidosa()))
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    def correr(*extra):
        return subprocess.run([sys.executable, "-m", "fotoproducto", str(entrada), str(salida),
                               "--plataforma", "mercadolibre", *extra],
                              cwd=BACKEND_DIR, capture_output=True, text=True, encoding="utf-8", env=entorno)

    r = correr("--quitar-fondo", "--centrar", "--espacio", "poco")
    assert r.returncode == 0, r.stderr
    r = correr("--centrar")  # sin quitar el fondo también funciona
    assert r.returncode == 0, r.stderr
