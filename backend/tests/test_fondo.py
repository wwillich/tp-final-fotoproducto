"""Tests de quitar el fondo (F3): marcas, watershed, composición sobre blanco y editor."""

import cv2
import numpy as np
import pytest

from conftest import escena, marcas
from fotoproducto import (
    EditorFotoProducto, MarcasInsuficientes, OpcionesEdicion, ProductoNoEncontrado,
)
from fotoproducto.fondo import (
    MARCA_FONDO, MARCA_PRODUCTO, ComponedorFondoBlanco, InterpretadorMarcas, QuitadorFondo,
)

CUADRADO = np.zeros((200, 200), bool)
CUADRADO[60:140, 60:140] = True


def iou(mascara: np.ndarray, real: np.ndarray = CUADRADO) -> float:
    m = mascara > 0
    return (m & real).sum() / (m | real).sum()


# --- InterpretadorMarcas ---------------------------------------------------------------

def test_interpretador_arma_los_marcadores():
    m = InterpretadorMarcas().interpretar(marcas(), (200, 200))
    assert m.dtype == np.int32 and m.shape == (200, 200)
    assert (m[90:110, 90:110] == MARCA_PRODUCTO).all()
    assert (m[5:25, 5:25] == MARCA_FONDO).all()
    assert m[100, 20] == 0 and m[40, 100] == 0  # sin marcar


@pytest.mark.parametrize("producto, fondo", [(False, True), (True, False), (False, False)])
def test_interpretador_exige_las_dos_clases(producto, fondo):
    with pytest.raises(MarcasInsuficientes):
        InterpretadorMarcas().interpretar(marcas(producto=producto, fondo=fondo), (200, 200))


def test_interpretador_reescala_las_marcas_sin_mezclar_etiquetas():
    chicas = marcas(100)  # la mitad del tamaño de la foto
    m = InterpretadorMarcas().interpretar(chicas, (200, 200))
    assert m.shape == (200, 200) and set(np.unique(m)) == {0, MARCA_FONDO, MARCA_PRODUCTO}


def test_interpretador_tolera_colores_mezclados_del_borde_del_pincel():
    img = np.zeros((50, 50, 3), np.uint8)
    img[:25] = (30, 220, 40)    # verde algo sucio
    img[25:] = (50, 30, 230)    # rojo algo sucio (BGR)
    m = InterpretadorMarcas().interpretar(img, (50, 50))
    assert (m[:25] == MARCA_PRODUCTO).all() and (m[25:] == MARCA_FONDO).all()


# --- QuitadorFondo ---------------------------------------------------------------------

def marcadores_de_prueba(lado: int = 200) -> np.ndarray:
    return InterpretadorMarcas().interpretar(marcas(lado), (lado, lado))


def test_watershed_separa_un_cuadrado_de_color_sobre_un_fondo_distinto():
    mascara = QuitadorFondo().mascara(escena(), marcadores_de_prueba())
    assert mascara.shape == (200, 200) and mascara.dtype == np.uint8
    assert set(np.unique(mascara)) <= {0, 255}
    assert iou(mascara) > 0.95


def test_trabaja_sobre_copia_reducida_y_devuelve_la_mascara_al_tamano_original():
    mascara = QuitadorFondo(lado_trabajo=100).mascara(escena(), marcadores_de_prueba())
    assert mascara.shape == (200, 200)
    assert iou(mascara) > 0.9


def test_no_modifica_los_marcadores_de_entrada():
    m = marcadores_de_prueba()
    antes = m.copy()
    QuitadorFondo().mascara(escena(), m)
    assert (m == antes).all()


def test_se_queda_con_la_componente_principal():
    img = np.full((200, 200, 3), 200, np.uint8)
    img[40:140, 40:140] = (30, 60, 200)   # grande
    img[160:185, 160:185] = (30, 60, 200)  # chico y separado
    m = np.zeros((200, 200, 3), np.uint8)
    m[80:100, 80:100] = (0, 255, 0)
    m[165:180, 165:180] = (0, 255, 0)      # también marcado como producto
    m[5:25, 5:25] = (0, 0, 255)
    mascara = QuitadorFondo().mascara(img, InterpretadorMarcas().interpretar(m, (200, 200)))
    assert mascara[170, 170] == 0 and mascara[100, 100] == 255


def test_producto_no_encontrado_si_la_mascara_queda_casi_vacia():
    with pytest.raises(ProductoNoEncontrado):
        QuitadorFondo(area_minima=0.9).mascara(escena(), marcadores_de_prueba())


# --- ComponedorFondoBlanco -------------------------------------------------------------

def test_componedor_deja_blanco_el_fondo_y_conserva_el_producto():
    img = escena()
    mascara = np.where(CUADRADO, 255, 0).astype(np.uint8)
    out = ComponedorFondoBlanco().componer(img, mascara)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert (out[:40, :40] == 255).all() and (out[160:, 160:] == 255).all()   # fondo lejos del borde
    assert (out[80:120, 80:120] == img[80:120, 80:120]).all()                # centro del producto


def test_componedor_suaviza_el_borde_sin_dejar_halo_del_fondo_original():
    img = np.full((400, 400, 3), 0, np.uint8)         # producto negro
    img[:, :] = 90                                    # fondo gris oscuro
    mascara = np.zeros((400, 400), np.uint8)
    mascara[100:300, 100:300] = 255
    out = ComponedorFondoBlanco(radio_relativo=0.02).componer(img, mascara)
    fila = out[200, 80:120, 0].astype(int)            # cruza el borde izquierdo
    assert fila[0] == 255 and fila[-1] == 90          # blanco afuera, producto adentro
    assert (np.diff(fila) <= 0).all()                 # transición monótona, sin escalón
    assert (fila == 255).any() and (fila == 90).any() and ((fila > 90) & (fila < 255)).any()  # hay borde suave
    # El borde suave cae dentro del producto: justo afuera de la máscara original ya es blanco puro.
    assert out[200, 99, 0] >= 250


# --- EditorFotoProducto ----------------------------------------------------------------

def test_editor_con_marcas_deja_el_fondo_blanco():
    editor, op = EditorFotoProducto(), OpcionesEdicion("mercadolibre", peso="maxima")
    con = cv2.imdecode(np.frombuffer(editor.procesar(escena(), op, marcas()).contenido, np.uint8), cv2.IMREAD_COLOR)
    sin = cv2.imdecode(np.frombuffer(editor.procesar(escena(), op).contenido, np.uint8), cv2.IMREAD_COLOR)
    assert con[10:60, 10:60].min() > 245                    # esquina: blanco
    assert abs(int(sin[10:60, 10:60].mean()) - 200) < 5     # sin marcas queda el gris original
    assert con[600, 600].tolist() == pytest.approx([30, 60, 200], abs=6)  # el producto no se toca


def test_editor_sin_las_dos_clases_de_marcas_falla_con_mensaje_claro():
    with pytest.raises(MarcasInsuficientes, match="Marcá al menos"):
        EditorFotoProducto().procesar(escena(), OpcionesEdicion("mercadolibre"), marcas(fondo=False))
