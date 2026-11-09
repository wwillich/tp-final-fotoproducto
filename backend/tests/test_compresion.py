"""Tests del compresor y de los codificadores (F2)."""

import cv2
import numpy as np
import pytest

from fotoproducto import EditorFotoProducto, OpcionesEdicion
from fotoproducto.compresion import AVISO_PESO, CODIFICADORES, KB, Compresor


def ruido(lado: int = 800) -> np.ndarray:
    """Ruido puro: casi incompresible (ninguna foto real es así)."""
    return np.random.default_rng(0).integers(0, 256, (lado, lado, 3), dtype=np.uint8)


def textura(lado: int = 1200, base: int = 150) -> np.ndarray:
    """Ruido suavizado: se parece más a una foto. A 1200 px pesa unos 170 KB a calidad 30 y 600 KB a 95."""
    chico = np.random.default_rng(0).integers(0, 256, (base, base, 3), dtype=np.uint8)
    return cv2.resize(chico, (lado, lado), interpolation=cv2.INTER_CUBIC)


def test_codificadores_devuelven_bytes_decodificables():
    img = ruido(64)
    for formato, mime in [("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("PNG", "image/png")]:
        codificador = CODIFICADORES[formato]
        assert codificador.tipo_mime == mime
        assert cv2.imdecode(np.frombuffer(codificador.codificar(img, 80), np.uint8), cv2.IMREAD_COLOR).shape == img.shape


def test_png_no_pierde_nada():
    img = ruido(64)
    decodificada = cv2.imdecode(np.frombuffer(CODIFICADORES["PNG"].codificar(img, 50), np.uint8), cv2.IMREAD_COLOR)
    assert (decodificada == img).all()


@pytest.mark.parametrize("formato", ["JPEG", "WEBP"])
@pytest.mark.parametrize("perfil, limite", [("liviano", 200 * KB), ("normal", 500 * KB)])
def test_respeta_el_limite_de_peso_con_la_mayor_calidad_posible(formato, perfil, limite):
    compresor, img = Compresor(), textura()
    r = compresor.comprimir(img, formato, perfil)
    assert len(r.contenido) <= limite and r.aviso is None
    if perfil == "liviano":
        assert r.calidad < compresor.calidad_maxima  # a calidad máxima no entra en 200 KB
    if r.calidad < compresor.calidad_maxima:
        # Con un punto más de calidad ya no entraría: es la mayor que cumple.
        assert len(CODIFICADORES[formato].codificar(img, r.calidad + 1)) > limite


def test_si_entra_a_la_mayor_calidad_usa_esa():
    compresor = Compresor()
    r = compresor.comprimir(np.full((400, 400, 3), 200, np.uint8), "JPEG", "liviano")
    assert r.calidad == compresor.calidad_maxima


def test_maxima_usa_la_calidad_maxima_sin_limite():
    compresor = Compresor()
    r = compresor.comprimir(textura(), "JPEG", "maxima")
    assert r.calidad == compresor.calidad_maxima and r.aviso is None
    assert len(r.contenido) > 500 * KB


def test_si_ni_con_la_calidad_minima_entra_avisa_y_entrega_la_mejor_posible():
    compresor = Compresor(perfiles={"diminuto": 1000})
    r = compresor.comprimir(ruido(), "JPEG", "diminuto")
    assert r.aviso == AVISO_PESO
    assert r.calidad == compresor.calidad_minima
    assert len(r.contenido) > 1000


def test_etiquetas_segun_psnr():
    c = Compresor()
    assert [c.etiquetar(p) for p in (45, 40, 37, 35, 31, 30, 20)] == [
        "excelente", "excelente", "muy buena", "muy buena", "buena", "buena", "aceptable"]


def test_etiqueta_sin_perdida_es_excelente_y_mas_compresion_baja_la_etiqueta():
    c, img = Compresor(), ruido()
    assert c.comprimir(img, "PNG", "maxima").etiqueta == "excelente"
    # Ruido en 200 KB: hay que comprimir mucho, la etiqueta no puede ser la mejor.
    assert c.comprimir(img, "JPEG", "liviano").etiqueta != "excelente"


def test_editor_aplica_el_perfil_de_peso():
    img = textura()
    editor = EditorFotoProducto()
    liviano = editor.procesar(img, OpcionesEdicion("mercadolibre", peso="liviano"))
    normal = editor.procesar(img, OpcionesEdicion("mercadolibre", peso="normal"))
    assert liviano.peso_bytes <= 200 * KB < normal.peso_bytes <= 500 * KB
    assert liviano.calidad and normal.calidad
    assert liviano.extension == ".jpg"
