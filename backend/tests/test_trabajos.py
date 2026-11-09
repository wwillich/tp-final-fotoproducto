"""Tests del guardado y la galería (F2): /api/trabajos y RepositorioTrabajos."""

import pytest

from app.config import STORAGE_DIR
from app.errors import TrabajoNoEncontrado
from app.repositorio import RepositorioTrabajos
from conftest import foto_bytes


@pytest.fixture(autouse=True)
def limpio(client):
    """Cada test arranca y termina sin trabajos guardados."""
    def vaciar():
        for t in client.get("/api/trabajos").json():
            client.delete(f"/api/trabajos/{t['id']}")
    vaciar()
    yield
    vaciar()


def crear(client, contenido=None, nombre="taza.png", **datos):
    datos = {"plataforma": "mercadolibre", **datos}
    return client.post("/api/trabajos", files={"archivo": (nombre, contenido or foto_bytes(800, 600), "image/png")},
                       data=datos)


def test_crear_guarda_original_y_resultado_y_devuelve_el_trabajo(client):
    original = foto_bytes(800, 600)
    r = crear(client, original, peso="liviano")
    assert r.status_code == 201
    t = r.json()
    assert (t["nombre_original"], t["plataforma"], t["formato"]) == ("taza.png", "mercadolibre", "JPEG")
    assert (t["ancho"], t["alto"]) == (1200, 1200)
    assert t["calidad"] in {"excelente", "muy buena", "buena", "aceptable"}
    assert t["opciones"]["peso"] == "liviano" and t["creado"]

    resultado = client.get(t["url"])
    assert resultado.status_code == 200 and resultado.headers["content-type"] == "image/jpeg"
    assert len(resultado.content) == t["peso_bytes"]
    assert client.get(t["url_original"]).content == original  # el original, tal cual se subió


def test_listar_devuelve_el_mas_nuevo_primero_y_obtener_uno(client):
    a = crear(client, nombre="a.png").json()
    b = crear(client, nombre="b.png").json()
    assert [t["id"] for t in client.get("/api/trabajos").json()] == [b["id"], a["id"]]
    assert client.get(f"/api/trabajos/{a['id']}").json() == a


def test_borrar_quita_el_trabajo_y_todos_sus_archivos(client):
    t = crear(client).json()
    assert (STORAGE_DIR / t["id"]).is_dir()
    assert client.delete(f"/api/trabajos/{t['id']}").status_code == 204
    assert not (STORAGE_DIR / t["id"]).exists()
    assert client.get(t["url"]).status_code == 404
    assert client.get(f"/api/trabajos/{t['id']}").status_code == 404
    assert client.get("/api/trabajos").json() == []


@pytest.mark.parametrize("id", ["0" * 32, "no-es-un-id"])
def test_404_si_no_existe_o_el_id_no_es_valido(client, id):
    for r in (client.get(f"/api/trabajos/{id}"), client.delete(f"/api/trabajos/{id}")):
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "TRABAJO_NO_ENCONTRADO"


@pytest.mark.parametrize("id", ["..", "../..", "a/b", "A" * 32, ""])
def test_el_repositorio_no_arma_rutas_con_ids_invalidos(id):
    repo = RepositorioTrabajos(STORAGE_DIR)
    for operacion in (repo.obtener, repo.borrar):
        with pytest.raises(TrabajoNoEncontrado):
            operacion(id)


def test_el_nombre_del_usuario_no_se_usa_para_nombrar_archivos(client):
    t = crear(client, nombre="../../evil name.png").json()
    assert sorted(p.name for p in (STORAGE_DIR / t["id"]).iterdir()) == ["meta.json", "original.png", "resultado.jpg"]


def test_un_archivo_invalido_no_guarda_nada(client):
    r = crear(client, b"no es una imagen")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_FILE"
    assert crear(client, plataforma="nada").status_code == 422
    assert not any(STORAGE_DIR.iterdir())


def test_crear_con_contorno_guarda_el_resultado_sin_fondo(client):
    import cv2
    import numpy as np

    from conftest import contorno, escena_ruidosa, png_bytes

    r = client.post("/api/trabajos", data={"plataforma": "mercadolibre", "peso": "maxima", "quitar_fondo": "true"}, files={
        "archivo": ("p.png", png_bytes(escena_ruidosa()), "image/png"),
        "contorno": ("c.png", png_bytes(contorno()), "image/png"),
    })
    assert r.status_code == 201
    guardado = cv2.imdecode(np.frombuffer(client.get(r.json()["url"]).content, np.uint8), cv2.IMREAD_COLOR)
    assert guardado[10:60, 10:60].min() > 245
    assert client.get(r.json()["url_original"]).content == png_bytes(escena_ruidosa())  # el original no se toca


def test_contorno_vacio_no_guarda_nada(client):
    from conftest import contorno, escena_ruidosa, png_bytes

    r = client.post("/api/trabajos", data={"plataforma": "mercadolibre"}, files={
        "archivo": ("p.png", png_bytes(escena_ruidosa()), "image/png"),
        "contorno": ("c.png", png_bytes(contorno(caja=(0, 0, 0, 0))), "image/png"),
    })
    assert r.status_code == 422 and not any(STORAGE_DIR.iterdir())


def test_peso_invalido_da_422(client):
    assert crear(client, peso="pesadisimo").status_code == 422


def test_los_trabajos_sobreviven_a_un_reinicio(client):
    t = crear(client).json()
    nuevo = RepositorioTrabajos(STORAGE_DIR)  # como si se reiniciara el servidor
    assert [x.id for x in nuevo.listar()] == [t["id"]]
    assert nuevo.obtener(t["id"]).nombre_original == "taza.png"
