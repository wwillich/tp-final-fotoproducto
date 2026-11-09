"""Tests de luz y color (F5): cada ajuste, el orden en el editor, la API y la línea de comandos."""

import os
import subprocess
import sys

import cv2
import numpy as np
import pytest

from conftest import BACKEND_DIR, contorno, escena_ruidosa, png_bytes
from fotoproducto import EditorFotoProducto, OpcionesEdicion
from fotoproducto.ajustes import Ajuste, AclararZonasOscuras, BrilloContraste, ColoresNaturales


def degradado(alto=120, ancho=160):
    """Imagen BGR con zonas oscuras, medias y claras, y los tres canales distintos."""
    azar = np.random.default_rng(1)
    base = np.linspace(20, 235, ancho, dtype=np.float32)[None, :, None] * np.ones((alto, 1, 3), np.float32)
    base *= np.array([0.8, 1.0, 1.1], np.float32)  # B, G, R
    return np.clip(base + azar.integers(-6, 7, base.shape), 0, 255).astype(np.uint8)


def luz(imagen):
    return cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY).astype(np.float32)


# --- Valores neutros --------------------------------------------------------------------

@pytest.mark.parametrize("ajuste", [BrilloContraste(), AclararZonasOscuras(), ColoresNaturales()])
def test_un_ajuste_neutro_no_cambia_la_imagen(ajuste):
    assert isinstance(ajuste, Ajuste)
    imagen = degradado()
    assert np.array_equal(ajuste.aplicar(imagen), imagen)


# --- BrilloContraste --------------------------------------------------------------------

def test_brillo_positivo_aclara_y_negativo_oscurece_sin_dar_vuelta_los_oscuros():
    imagen = degradado()
    assert luz(BrilloContraste(brillo=40).aplicar(imagen)).mean() > luz(imagen).mean() + 20
    oscura = BrilloContraste(brillo=-60).aplicar(imagen)
    assert luz(oscura).mean() < luz(imagen).mean() - 20
    assert oscura[:, :5].max() < 30    # los píxeles más oscuros se quedan negros, no se vuelven claros


def test_contraste_separa_los_claros_de_los_oscuros():
    imagen = degradado()
    mas = BrilloContraste(contraste=50).aplicar(imagen)
    menos = BrilloContraste(contraste=-50).aplicar(imagen)
    assert luz(mas).std() > luz(imagen).std() > luz(menos).std()


def test_brillo_y_contraste_en_los_extremos_dan_imagenes_validas():
    for brillo, contraste in [(-100, -100), (100, 100), (100, -100), (-100, 100)]:
        out = BrilloContraste(brillo, contraste).aplicar(degradado())
        assert out.dtype == np.uint8 and out.shape == degradado().shape


# --- AclararZonasOscuras ----------------------------------------------------------------

def sombras():
    """Detalle de poco contraste en una zona oscura, y una zona clara al lado."""
    azar = np.random.default_rng(2)
    img = np.full((160, 240, 3), 200, np.uint8)
    img[:, :120] = np.clip(40 + azar.integers(-12, 13, (160, 120, 1)), 0, 255)
    return img


def test_aclarar_zonas_oscuras_sube_la_luz_de_las_sombras_y_deja_casi_igual_lo_claro():
    imagen = sombras()
    out = AclararZonasOscuras(1.0).aplicar(imagen)
    assert luz(out)[:, :120].mean() > luz(imagen)[:, :120].mean() + 15
    assert abs(luz(out)[:, 130:].mean() - luz(imagen)[:, 130:].mean()) < 10


def test_mas_intensidad_aclara_mas():
    imagen = sombras()
    medios = [luz(AclararZonasOscuras(i).aplicar(imagen))[:, :120].mean() for i in (0.0, 0.5, 1.0)]
    assert medios[0] < medios[1] < medios[2]


def test_aclarar_conserva_el_color():
    imagen = np.full((100, 100, 3), (40, 60, 120), np.uint8)
    imagen += np.random.default_rng(3).integers(0, 8, imagen.shape, dtype=np.uint8)
    out = AclararZonasOscuras(0.8).aplicar(imagen)
    assert out[..., 2].mean() > out[..., 0].mean()   # sigue siendo rojizo


# --- ColoresNaturales -------------------------------------------------------------------

def con_luz_amarilla():
    """Una escena gris con la luz cálida: poco azul."""
    azar = np.random.default_rng(4)
    gris = azar.integers(80, 241, (100, 100, 1)).astype(np.float32)
    return np.clip(gris * np.array([0.6, 0.85, 1.0], np.float32), 0, 255).astype(np.uint8)  # B, G, R


def test_colores_naturales_corrige_la_dominante_de_color():
    imagen = con_luz_amarilla()
    out = ColoresNaturales(activo=True).aplicar(imagen)
    antes = imagen.reshape(-1, 3).mean(axis=0)
    despues = out.reshape(-1, 3).mean(axis=0)
    assert antes.max() - antes.min() > 40
    assert despues.max() - despues.min() < 15          # los tres canales quedan parejos


def test_colores_naturales_no_toca_una_foto_que_ya_tiene_blanco_puro():
    azar = np.random.default_rng(5)
    imagen = azar.integers(0, 256, (80, 80, 3)).astype(np.uint8)
    assert np.abs(ColoresNaturales(activo=True).aplicar(imagen).astype(int) - imagen).max() <= 3


def test_colores_naturales_no_multiplica_sin_limite_una_foto_muy_oscura():
    oscura = np.full((50, 50, 3), 5, np.uint8)
    assert ColoresNaturales(activo=True).aplicar(oscura).max() <= 10   # tope de ganancia = 2


# --- Editor -----------------------------------------------------------------------------

def decodificar(contenido: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)


def test_el_editor_aplica_los_ajustes():
    editor = EditorFotoProducto()
    base = OpcionesEdicion("mercadolibre", peso="maxima")
    claro = OpcionesEdicion("mercadolibre", peso="maxima", brillo=50)
    imagen = degradado()
    assert luz(decodificar(editor.procesar(imagen, claro).contenido)).mean() > \
        luz(decodificar(editor.procesar(imagen, base).contenido)).mean() + 20


def test_los_ajustes_van_antes_del_fondo_blanco_y_no_lo_tinen():
    editor = EditorFotoProducto()
    escena = escena_ruidosa()
    op = OpcionesEdicion("mercadolibre", peso="maxima", brillo=-50, contraste=30, aclarar_oscuras=0.5,
                         colores_naturales=True, quitar_fondo=True)
    out = decodificar(editor.procesar(escena, op, contorno()).contenido)
    assert out[10:60, 10:60].min() > 245   # el fondo sigue siendo blanco puro, aunque se oscureció la foto


def test_sin_ajustes_el_resultado_no_cambia():
    editor = EditorFotoProducto()
    imagen = degradado()
    a = editor.procesar(imagen, OpcionesEdicion("mercadolibre")).contenido
    b = editor.procesar(imagen, OpcionesEdicion("mercadolibre", brillo=0, contraste=0, aclarar_oscuras=0,
                                                colores_naturales=False)).contenido
    assert a == b


# --- API --------------------------------------------------------------------------------

def vista_previa(client, **datos):
    return client.post("/api/vista-previa", data={"plataforma": "mercadolibre", "peso": "maxima", **datos},
                       files={"archivo": ("f.png", png_bytes(degradado()), "image/png")})


def test_api_aplica_brillo(client):
    base = decodificar(vista_previa(client).content)
    claro = decodificar(vista_previa(client, brillo="50").content)
    assert luz(claro).mean() > luz(base).mean() + 20


def test_api_acepta_todos_los_ajustes(client):
    r = vista_previa(client, brillo="-20", contraste="20", aclarar_oscuras="0.5", colores_naturales="true")
    assert r.status_code == 200


@pytest.mark.parametrize("campo, valor", [("brillo", "101"), ("brillo", "-101"), ("contraste", "200"),
                                          ("aclarar_oscuras", "1.5"), ("aclarar_oscuras", "-0.1")])
def test_api_rechaza_valores_fuera_de_rango(client, campo, valor):
    assert vista_previa(client, **{campo: valor}).status_code == 422


# --- Línea de comandos ------------------------------------------------------------------

def correr(*args):
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-m", "fotoproducto", *map(str, args)],
                          cwd=BACKEND_DIR, capture_output=True, text=True, encoding="utf-8", env=entorno)


def test_cli_ajustes(tmp_path):
    entrada, salida = tmp_path / "in.png", tmp_path / "out.jpg"
    entrada.write_bytes(png_bytes(degradado()))
    r = correr(entrada, salida, "--plataforma", "mercadolibre", "--brillo", "30", "--contraste", "-10",
               "--aclarar-oscuras", "0.5", "--colores-naturales")
    assert r.returncode == 0, r.stderr


def test_cli_rechaza_ajustes_fuera_de_rango(tmp_path):
    for opcion, valor in [("--brillo", "500"), ("--aclarar-oscuras", "2")]:
        r = correr(tmp_path / "in.png", tmp_path / "out.jpg", "--plataforma", "mercadolibre", opcion, valor)
        assert r.returncode != 0 and "tiene que estar entre" in r.stderr
