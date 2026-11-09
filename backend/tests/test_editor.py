"""Tests del catálogo de plataformas y del editor (F1)."""

import cv2
import numpy as np
import pytest

from fotoproducto import CatalogoPlataformas, EditorFotoProducto, OpcionesEdicion, PlataformaDesconocida


def decodificar(contenido: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)


def test_catalogo_lista_y_obtiene():
    catalogo = CatalogoPlataformas()
    assert [p.clave for p in catalogo.listar()][0] == "mercadolibre"
    p = catalogo.obtener("instagram_vertical")
    assert (p.ancho, p.alto, p.formato) == (1080, 1350, "JPEG")


def test_catalogo_plataforma_desconocida():
    with pytest.raises(PlataformaDesconocida):
        CatalogoPlataformas().obtener("nada")


@pytest.mark.parametrize("clave, formato", [("mercadolibre", "JPEG"), ("tiendanube", "WEBP")])
def test_editor_devuelve_tamano_exacto_y_formato(clave, formato):
    plataforma = CatalogoPlataformas().obtener(clave)
    r = EditorFotoProducto().procesar(np.zeros((300, 500, 3), np.uint8), OpcionesEdicion(clave))
    assert r.formato == formato
    assert (r.ancho, r.alto) == (plataforma.ancho, plataforma.alto)
    assert decodificar(r.contenido).shape[:2] == (plataforma.alto, plataforma.ancho)
    assert r.peso_bytes == len(r.contenido)


def test_editor_avisa_foto_chica_y_no_avisa_foto_grande():
    editor, op = EditorFotoProducto(), OpcionesEdicion("mercadolibre")
    chica = editor.procesar(np.zeros((300, 300, 3), np.uint8), op)
    assert chica.avisos == ["Tu foto es más chica de lo que pide Mercado Libre. Puede verse un poco borrosa."]
    assert EditorFotoProducto().procesar(np.zeros((2000, 2000, 3), np.uint8), op).avisos == []


def test_editor_recortar_cambia_el_resultado_segun_la_posicion():
    img = np.zeros((300, 600, 3), np.uint8)
    img[:, 300:] = 255  # mitad izquierda negra, derecha blanca
    editor = EditorFotoProducto()
    izquierda = decodificar(editor.procesar(img, OpcionesEdicion("mercadolibre", "recortar", posicion_x=0)).contenido)
    derecha = decodificar(editor.procesar(img, OpcionesEdicion("mercadolibre", "recortar", posicion_x=1)).contenido)
    assert izquierda.mean() < 30 and derecha.mean() > 225
