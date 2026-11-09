"""Tests de quitar el fondo (F3): grabCut con contorno, composición sobre blanco y editor."""

import cv2
import numpy as np
import pytest

from conftest import contorno, escena_ruidosa
from fotoproducto import ContornoInvalido, EditorFotoProducto, OpcionesEdicion, ProductoNoEncontrado
from fotoproducto.fondo import ComponedorFondoBlanco, QuitadorFondo

CUADRADO = np.zeros((200, 200), bool)
CUADRADO[60:140, 60:140] = True

# Producto corrido a un costado: la elipse automática (centrada) no lo cubre bien.
CAJA_LATERAL = (70, 130, 120, 185)
LATERAL = np.zeros((200, 200), bool)
LATERAL[70:130, 120:185] = True


def iou(mascara: np.ndarray, real: np.ndarray = CUADRADO) -> float:
    m = mascara > 0
    return (m & real).sum() / (m | real).sum()


# --- QuitadorFondo ---------------------------------------------------------------------

def test_automatico_separa_un_producto_centrado():
    mascara = QuitadorFondo().mascara(escena_ruidosa())
    assert mascara.shape == (200, 200) and mascara.dtype == np.uint8
    assert set(np.unique(mascara)) <= {0, 255}
    assert iou(mascara) > 0.95


def test_con_contorno_separa_un_producto_corrido():
    escena = escena_ruidosa(caja=CAJA_LATERAL)
    mascara = QuitadorFondo().mascara(escena, contorno(caja=(60, 140, 110, 195)))
    assert iou(mascara, LATERAL) > 0.95


def test_el_contorno_puede_venir_en_gris_y_de_otro_tamano():
    gris = cv2.cvtColor(contorno(100, caja=(25, 75, 25, 75)), cv2.COLOR_BGR2GRAY)  # la mitad de la foto
    assert iou(QuitadorFondo().mascara(escena_ruidosa(), gris)) > 0.95


def test_trabaja_sobre_copia_reducida_y_devuelve_la_mascara_al_tamano_original():
    mascara = QuitadorFondo(lado_trabajo=100).mascara(escena_ruidosa(), contorno())
    assert mascara.shape == (200, 200)
    assert iou(mascara) > 0.9


def test_se_queda_con_la_componente_principal():
    img = escena_ruidosa()
    img[160:185, 160:185] = (30, 60, 200)  # mancha del mismo color, separada del producto
    mascara = QuitadorFondo().mascara(img, contorno(caja=(50, 190, 50, 190)))
    assert mascara[170, 170] == 0 and mascara[100, 100] == 255


@pytest.mark.parametrize("zona", [0, 255])
def test_contorno_invalido_si_no_encierra_nada_o_es_toda_la_foto(zona):
    with pytest.raises(ContornoInvalido, match="no encierra"):
        QuitadorFondo().mascara(escena_ruidosa(), np.full((200, 200), zona, np.uint8))


def test_producto_no_encontrado_si_la_mascara_queda_casi_vacia():
    with pytest.raises(ProductoNoEncontrado):
        QuitadorFondo(area_minima=0.9).mascara(escena_ruidosa())


# --- ComponedorFondoBlanco -------------------------------------------------------------

def test_componedor_deja_blanco_el_fondo_y_conserva_el_producto():
    img = escena_ruidosa()
    mascara = np.where(CUADRADO, 255, 0).astype(np.uint8)
    out = ComponedorFondoBlanco().componer(img, mascara)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert (out[:40, :40] == 255).all() and (out[160:, 160:] == 255).all()   # fondo lejos del borde
    assert (out[80:120, 80:120] == img[80:120, 80:120]).all()                # centro del producto


def test_componedor_suaviza_el_borde_sin_dejar_halo_del_fondo_original():
    img = np.full((400, 400, 3), 90, np.uint8)        # fondo gris oscuro
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

def decodificar(contenido: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)


def test_editor_con_quitar_fondo_deja_el_fondo_blanco():
    editor, escena = EditorFotoProducto(), escena_ruidosa()
    op = OpcionesEdicion("mercadolibre", peso="maxima", quitar_fondo=True)
    con = decodificar(editor.procesar(escena, op).contenido)
    sin = decodificar(editor.procesar(escena, OpcionesEdicion("mercadolibre", peso="maxima")).contenido)
    assert con[10:60, 10:60].min() > 245                    # esquina: blanco
    assert abs(int(sin[10:60, 10:60].mean()) - 200) < 5     # sin pedirlo queda el gris original
    assert con[600, 600].tolist() == pytest.approx([30, 60, 200], abs=14)  # el producto no se toca


def test_editor_un_contorno_implica_quitar_el_fondo():
    op = OpcionesEdicion("mercadolibre", peso="maxima")  # quitar_fondo = False
    con = decodificar(EditorFotoProducto().procesar(escena_ruidosa(), op, contorno()).contenido)
    assert con[10:60, 10:60].min() > 245


def test_editor_contorno_vacio_falla_con_mensaje_claro():
    vacio = np.zeros((200, 200, 3), np.uint8)
    with pytest.raises(ContornoInvalido, match="Dibujalo de nuevo"):
        EditorFotoProducto().procesar(escena_ruidosa(), OpcionesEdicion("mercadolibre"), vacio)
