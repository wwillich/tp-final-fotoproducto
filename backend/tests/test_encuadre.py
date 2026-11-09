"""Tests de los adaptadores de proporción y del redimensionador (F1)."""

import cv2
import numpy as np
import pytest

from fotoproducto.encuadre import ADAPTADORES, AgregarBordes, Recortar
from fotoproducto.redimension import Redimensionador


def gradiente(ancho: int, alto: int) -> np.ndarray:
    """Imagen donde cada columna tiene un valor distinto (0-250), para saber qué parte se recortó."""
    col = np.linspace(0, 250, ancho).astype(np.uint8)
    return np.dstack([np.tile(col, (alto, 1))] * 3)


def test_bordes_foto_ancha_da_proporcion_y_bordes_blancos():
    img = np.zeros((100, 200, 3), np.uint8)
    out = AgregarBordes().adaptar(img, 1080, 1080)
    assert out.shape[:2] == (200, 200)
    assert (out[:50] == 255).all() and (out[150:] == 255).all()  # arriba y abajo blancos
    assert (out[50:150] == 0).all()                              # la foto, intacta y centrada


def test_bordes_foto_alta_completa_a_los_costados():
    img = np.zeros((200, 100, 3), np.uint8)
    out = AgregarBordes().adaptar(img, 1080, 1080)
    assert out.shape[:2] == (200, 200)
    assert (out[:, :50] == 255).all() and (out[:, 150:] == 255).all()


def test_bordes_no_toca_una_foto_que_ya_tiene_la_proporcion():
    img = np.zeros((135, 108, 3), np.uint8)
    assert AgregarBordes().adaptar(img, 1080, 1350).shape == img.shape


@pytest.mark.parametrize("posicion, esperado", [(0, 0), (0.5, 50), (1, 100), (0.3, 30)])
def test_recortar_foto_ancha_conserva_la_parte_de_la_posicion(posicion, esperado):
    out = Recortar(posicion_x=posicion).adaptar(gradiente(200, 100), 1, 1)
    assert out.shape[:2] == (100, 100)
    assert out[0, 0, 0] == gradiente(200, 100)[0, esperado, 0]


@pytest.mark.parametrize("posicion, esperado", [(0, 0), (0.5, 50), (1, 100), (0.3, 30)])
def test_recortar_foto_alta_conserva_la_parte_de_la_posicion(posicion, esperado):
    img = gradiente(200, 100).transpose(1, 0, 2).copy()  # 200 de alto × 100 de ancho, varía por fila
    out = Recortar(posicion_y=posicion).adaptar(img, 1, 1)
    assert out.shape[:2] == (100, 100)
    assert out[0, 0, 0] == img[esperado, 0, 0]


def test_recortar_ignora_la_posicion_del_eje_sin_sobrante():
    img = gradiente(200, 100)  # ancha: solo importa posicion_x
    assert (Recortar(0.2, 0).adaptar(img, 1, 1) == Recortar(0.2, 1).adaptar(img, 1, 1)).all()


def test_recortar_posicion_fuera_de_rango_se_limita():
    img = gradiente(200, 100)
    assert (Recortar(-3).adaptar(img, 1, 1) == Recortar(0).adaptar(img, 1, 1)).all()
    assert (Recortar(7).adaptar(img, 1, 1) == Recortar(1).adaptar(img, 1, 1)).all()


def test_registro_de_adaptadores():
    assert isinstance(ADAPTADORES["bordes"](0.5, 0.5), AgregarBordes)
    assert isinstance(ADAPTADORES["recortar"](1.0, 0.0), Recortar)


def test_redimensionador_usa_area_al_reducir_y_cubic_al_ampliar():
    img = np.random.default_rng(0).integers(0, 256, (100, 100, 3), dtype=np.uint8)
    r = Redimensionador()

    chica, amplio = r.redimensionar(img, 50, 50)
    assert not amplio
    assert (chica == cv2.resize(img, (50, 50), interpolation=cv2.INTER_AREA)).all()

    grande, amplio = r.redimensionar(img, 200, 200)
    assert amplio
    assert (grande == cv2.resize(img, (200, 200), interpolation=cv2.INTER_CUBIC)).all()
