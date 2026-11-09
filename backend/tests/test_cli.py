"""Tests de la línea de comandos."""

import subprocess
import sys

import cv2

from conftest import BACKEND_DIR, foto_bytes


def correr(*args):
    return subprocess.run([sys.executable, "-m", "fotoproducto", *map(str, args)],
                          cwd=BACKEND_DIR, capture_output=True, text=True)


def test_cli_genera_el_archivo(tmp_path):
    entrada, salida = tmp_path / "in.png", tmp_path / "out.jpg"
    entrada.write_bytes(foto_bytes(800, 600))
    r = correr(entrada, salida, "--plataforma", "instagram_vertical", "--adaptacion", "recortar",
               "--posicion-x", "0", "--posicion-y", "1")
    assert r.returncode == 0, r.stderr
    assert cv2.imread(str(salida)).shape[:2] == (1350, 1080)


def test_cli_rechaza_posicion_fuera_de_rango(tmp_path):
    for opcion in ("--posicion-x", "--posicion-y"):
        r = correr(tmp_path / "in.png", tmp_path / "out.jpg", "--plataforma", "mercadolibre", opcion, "2")
        assert r.returncode != 0 and "entre 0 y 1" in r.stderr


def test_cli_error_sale_por_stderr_con_codigo_distinto_de_cero(tmp_path):
    malo = tmp_path / "malo.png"
    malo.write_bytes(b"no es una imagen")
    r = correr(malo, tmp_path / "out.jpg", "--plataforma", "mercadolibre")
    assert r.returncode != 0 and "Error:" in r.stderr
    r = correr(tmp_path / "no_existe.png", tmp_path / "out.jpg", "--plataforma", "mercadolibre")
    assert r.returncode != 0 and "Error:" in r.stderr
