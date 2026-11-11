"""Pruebas con fotos reales de productos (las que haya en tests/fotos/; si no hay, se saltan)."""

from pathlib import Path

import pytest

from fotoproducto import CatalogoPlataformas, EditorFotoProducto, OpcionesEdicion, read_photo

CARPETA = Path(__file__).with_name("fotos")
FOTOS = sorted(p for p in CARPETA.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
PLATAFORMAS = [p.clave for p in CatalogoPlataformas().listar()]
LIMITE_LIVIANO = 200 * 1024

pytestmark = pytest.mark.skipif(not FOTOS, reason="no hay fotos en tests/fotos/")


@pytest.fixture(scope="module")
def editor() -> EditorFotoProducto:
    return EditorFotoProducto()


@pytest.mark.parametrize("plataforma", PLATAFORMAS)
@pytest.mark.parametrize("foto", FOTOS, ids=lambda p: p.name)
def test_sale_con_el_tamano_de_la_plataforma(editor, foto, plataforma):
    """La foto real sale exactamente del tamaño pedido, con cualquier adaptación."""
    imagen = read_photo(foto.read_bytes()).image
    objetivo = CatalogoPlataformas().obtener(plataforma)
    for adaptacion in ("bordes", "recortar"):
        resultado = editor.procesar(imagen, OpcionesEdicion(plataforma=plataforma, adaptacion=adaptacion))
        assert (resultado.ancho, resultado.alto) == (objetivo.ancho, objetivo.alto)


@pytest.mark.parametrize("foto", FOTOS, ids=lambda p: p.name)
def test_respeta_el_peso_liviano(editor, foto):
    """El perfil liviano baja de 200 KB (o avisa que no pudo)."""
    imagen = read_photo(foto.read_bytes()).image
    resultado = editor.procesar(imagen, OpcionesEdicion(plataforma="mercadolibre", peso="liviano"))
    assert resultado.peso_bytes <= LIMITE_LIVIANO or resultado.avisos


@pytest.mark.parametrize("foto", FOTOS, ids=lambda p: p.name)
def test_todas_las_etapas_juntas(editor, foto):
    """Luz, color, centrado y nitidez activados a la vez no rompen con una foto real."""
    imagen = read_photo(foto.read_bytes()).image
    opciones = OpcionesEdicion(
        plataforma="instagram_vertical", centrar=True, brillo=10, contraste=10,
        aclarar_oscuras=0.5, colores_naturales=True, nitidez="poco",
    )
    resultado = editor.procesar(imagen, opciones)
    assert (resultado.ancho, resultado.alto) == (1080, 1350)
    assert resultado.contenido
