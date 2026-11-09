"""Línea de comandos: python -m fotoproducto ENTRADA SALIDA --plataforma mercadolibre [opciones]."""

import argparse
import sys
from pathlib import Path

from fotoproducto.editor import EditorFotoProducto, OpcionesEdicion
from fotoproducto.encuadre import ADAPTADORES
from fotoproducto.exceptions import ErrorFotoProducto
from fotoproducto.imageio import read_photo


def fraccion(texto: str) -> float:
    """Tipo de argparse: número entre 0 y 1."""
    valor = float(texto)
    if not 0 <= valor <= 1:
        raise argparse.ArgumentTypeError("tiene que estar entre 0 y 1")
    return valor


def main(argv: list[str] | None = None) -> int:
    """Procesa una foto. Devuelve 0 si salió bien; ante un error, lo informa por stderr y devuelve 1."""
    editor = EditorFotoProducto()
    parser = argparse.ArgumentParser(prog="fotoproducto", description="Deja una foto lista para publicar.")
    parser.add_argument("entrada", help="foto original")
    parser.add_argument("salida", help="archivo donde guardar el resultado")
    parser.add_argument("--plataforma", required=True, choices=[p.clave for p in editor.catalogo.listar()])
    parser.add_argument("--adaptacion", choices=list(ADAPTADORES), default="bordes",
                        help="qué hacer si la foto no entra en el formato (por defecto: bordes)")
    parser.add_argument("--posicion-x", type=fraccion, default=0.5,
                        help="al recortar, de 0 (conserva la izquierda) a 1 (la derecha); por defecto 0.5")
    parser.add_argument("--posicion-y", type=fraccion, default=0.5,
                        help="al recortar, de 0 (conserva la parte de arriba) a 1 (la de abajo); por defecto 0.5")
    parser.add_argument("--peso", choices=list(editor.compresor.perfiles), default="normal",
                        help="peso del archivo: liviano (hasta 200 KB), normal (hasta 500 KB) o maxima calidad (por defecto: normal)")
    args = parser.parse_args(argv)

    try:
        foto = read_photo(Path(args.entrada).read_bytes())
        opciones = OpcionesEdicion(plataforma=args.plataforma, adaptacion=args.adaptacion,
                                   posicion_x=args.posicion_x, posicion_y=args.posicion_y, peso=args.peso)
        resultado = editor.procesar(foto.image, opciones)
        Path(args.salida).write_bytes(resultado.contenido)
    except (ErrorFotoProducto, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for aviso in resultado.avisos:
        print(f"Aviso: {aviso}", file=sys.stderr)
    print(f"Guardado en {args.salida}: {resultado.ancho} × {resultado.alto} · "
          f"{resultado.formato} · {resultado.peso_bytes // 1024} KB · calidad {resultado.calidad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
