"""Tests de la línea de comandos."""

import os
import subprocess
import sys

import cv2

from conftest import BACKEND_DIR, contorno, escena_ruidosa, foto_bytes, png_bytes


def correr(*args):
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # misma codificación a ambos lados del pipe
    return subprocess.run([sys.executable, "-m", "fotoproducto", *map(str, args)],
                          cwd=BACKEND_DIR, capture_output=True, text=True, encoding="utf-8", env=entorno)


def test_cli_genera_el_archivo(tmp_path):
    entrada, salida = tmp_path / "in.png", tmp_path / "out.jpg"
    entrada.write_bytes(foto_bytes(800, 600))
    r = correr(entrada, salida, "--plataforma", "instagram_vertical", "--adaptacion", "recortar",
               "--posicion-x", "0", "--posicion-y", "1", "--peso", "liviano")
    assert r.returncode == 0, r.stderr
    assert "calidad" in r.stdout
    assert cv2.imread(str(salida)).shape[:2] == (1350, 1080)


def test_cli_quitar_fondo_automatico(tmp_path):
    entrada, salida = tmp_path / "in.png", tmp_path / "out.jpg"
    entrada.write_bytes(png_bytes(escena_ruidosa()))
    r = correr(entrada, salida, "--plataforma", "mercadolibre", "--peso", "maxima", "--quitar-fondo")
    assert r.returncode == 0, r.stderr
    assert cv2.imread(str(salida))[10:60, 10:60].min() > 245


def test_cli_con_contorno_quita_el_fondo(tmp_path):
    entrada, contorno_png, salida = tmp_path / "in.png", tmp_path / "contorno.png", tmp_path / "out.jpg"
    entrada.write_bytes(png_bytes(escena_ruidosa()))
    contorno_png.write_bytes(png_bytes(contorno()))
    r = correr(entrada, salida, "--plataforma", "mercadolibre", "--peso", "maxima", "--contorno", contorno_png)
    assert r.returncode == 0, r.stderr
    assert cv2.imread(str(salida))[10:60, 10:60].min() > 245


def test_cli_contorno_vacio_o_inexistente_fallan_por_stderr(tmp_path):
    entrada, contorno_png = tmp_path / "in.png", tmp_path / "contorno.png"
    entrada.write_bytes(png_bytes(escena_ruidosa()))
    contorno_png.write_bytes(png_bytes(contorno(caja=(0, 0, 0, 0))))
    r = correr(entrada, tmp_path / "out.jpg", "--plataforma", "mercadolibre", "--contorno", contorno_png)
    assert r.returncode != 0 and "no encierra" in r.stderr
    r = correr(entrada, tmp_path / "out.jpg", "--plataforma", "mercadolibre", "--contorno", tmp_path / "no_existe.png")
    assert r.returncode != 0 and "Error:" in r.stderr


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
