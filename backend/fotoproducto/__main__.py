"""Línea de comandos: python -m fotoproducto ENTRADA SALIDA --plataforma mercadolibre [opciones]."""

import argparse
import sys
from pathlib import Path
from typing import Callable

from fotoproducto.ajustes import NIVELES_NITIDEZ
from fotoproducto.editor import EditorFotoProducto, OpcionesEdicion
from fotoproducto.encuadre import ADAPTADORES, ESPACIOS
from fotoproducto.exceptions import ErrorFotoProducto
from fotoproducto.imageio import read_photo


def numero(minimo: float, maximo: float) -> Callable[[str], float]:
    """Tipo de argparse: número entre `minimo` y `maximo`."""
    def convertir(texto: str) -> float:
        """Convierte el texto y verifica que esté dentro del rango."""
        valor = float(texto)
        if not minimo <= valor <= maximo:
            raise argparse.ArgumentTypeError(f"tiene que estar entre {minimo:g} y {maximo:g}")
        return valor
    return convertir


fraccion = numero(0, 1)


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
                        help="peso del archivo: liviano (hasta 200 KB), normal (hasta 500 KB) "
                             "o maxima calidad (por defecto: normal)")
    parser.add_argument("--quitar-fondo", action="store_true",
                        help="deja el producto sobre fondo blanco (lo detecta solo)")
    parser.add_argument("--contorno", help="imagen con una zona clara que rodea el producto; "
                                           "guía para quitar el fondo o centrar (solo, quita el fondo)")
    parser.add_argument("--centrar", action="store_true",
                        help="centra el producto en la foto (con o sin --quitar-fondo)")
    parser.add_argument("--espacio", choices=list(ESPACIOS), default="normal",
                        help="espacio alrededor del producto al centrarlo (por defecto: normal)")
    parser.add_argument("--brillo", type=numero(-100, 100), default=0, help="de -100 (más oscuro) a 100 (más claro)")
    parser.add_argument("--contraste", type=numero(-100, 100), default=0,
                        help="de -100 (más apagado) a 100 (más marcado)")
    parser.add_argument("--aclarar-oscuras", type=numero(0, 1), default=0,
                        help="aclara las zonas oscuras, de 0 (nada) a 1 (mucho)")
    parser.add_argument("--colores-naturales", action="store_true",
                        help="corrige el tono amarillento o azulado de la luz")
    parser.add_argument("--nitidez", choices=list(NIVELES_NITIDEZ), default="nada",
                        help="realce de los bordes, aplicado al tamaño final (por defecto: nada)")
    args = parser.parse_args(argv)

    try:
        foto = read_photo(Path(args.entrada).read_bytes())
        contorno = read_photo(Path(args.contorno).read_bytes()).image if args.contorno else None
        opciones = OpcionesEdicion(plataforma=args.plataforma, adaptacion=args.adaptacion,
                                   posicion_x=args.posicion_x, posicion_y=args.posicion_y, peso=args.peso,
                                   quitar_fondo=args.quitar_fondo, centrar=args.centrar, espacio=args.espacio,
                                   brillo=args.brillo, contraste=args.contraste,
                                   aclarar_oscuras=args.aclarar_oscuras, colores_naturales=args.colores_naturales,
                                   nitidez=args.nitidez)
        resultado = editor.procesar(foto.image, opciones, contorno)
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
