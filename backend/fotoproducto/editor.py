"""Editor: orquesta las etapas del procesamiento en el orden correcto."""

from dataclasses import dataclass, field

import numpy as np

from fotoproducto.compresion import Compresor
from fotoproducto.encuadre import ADAPTADORES, ESPACIOS, Centrador
from fotoproducto.fondo import ComponedorFondoBlanco, QuitadorFondo
from fotoproducto.plataformas import CatalogoPlataformas
from fotoproducto.redimension import Redimensionador


@dataclass
class OpcionesEdicion:
    """Lo que el usuario eligió. Se irán sumando campos a medida que haya más etapas."""

    plataforma: str
    adaptacion: str = "bordes"  # clave de ADAPTADORES
    posicion_x: float = 0.5     # al recortar: 0 conserva la izquierda … 1 la derecha
    posicion_y: float = 0.5     # al recortar: 0 conserva la parte de arriba … 1 la de abajo
    peso: str = "normal"        # perfil de peso del Compresor: liviano, normal o maxima
    quitar_fondo: bool = False  # dejar el producto sobre fondo blanco
    centrar: bool = False       # centrar el producto (con o sin quitar el fondo)
    espacio: str = "normal"     # espacio alrededor al centrar: clave de ESPACIOS


@dataclass
class ResultadoEdicion:
    """La imagen final ya codificada, con sus datos."""

    contenido: bytes
    formato: str
    tipo_mime: str
    extension: str              # con punto: ".jpg", ".webp"…
    ancho: int
    alto: int
    peso_bytes: int
    calidad: str                # etiqueta: excelente, muy buena, buena o aceptable
    avisos: list[str] = field(default_factory=list)


class EditorFotoProducto:
    """Aplica las etapas de edición a una foto y devuelve el resultado listo para publicar."""

    def __init__(self, catalogo: CatalogoPlataformas | None = None,
                 redimensionador: Redimensionador | None = None,
                 compresor: Compresor | None = None,
                 quitador: QuitadorFondo | None = None,
                 componedor: ComponedorFondoBlanco | None = None) -> None:
        self.catalogo = catalogo or CatalogoPlataformas()
        self.redimensionador = redimensionador or Redimensionador()
        self.compresor = compresor or Compresor()
        self.quitador = quitador or QuitadorFondo()
        self.componedor = componedor or ComponedorFondoBlanco()

    def procesar(self, imagen: np.ndarray, opciones: OpcionesEdicion,
                 contorno: np.ndarray | None = None) -> ResultadoEdicion:
        """Quita el fondo (si se pidió), adapta a la proporción de la plataforma, cambia al
        tamaño exacto y comprime.

        `contorno` es opcional: una imagen donde lo claro encierra el producto. Si se da,
        el fondo se quita aunque `opciones.quitar_fondo` sea False.
        """
        plataforma = self.catalogo.obtener(opciones.plataforma)
        adaptador = ADAPTADORES[opciones.adaptacion](opciones.posicion_x, opciones.posicion_y)

        if opciones.quitar_fondo or opciones.centrar or contorno is not None:
            # La máscara sirve para las dos cosas: saber dónde está el producto (centrar) y qué es fondo (quitarlo).
            mascara = self.quitador.mascara(imagen, contorno)
            # Un contorno solo, sin pedir nada más, quita el fondo; si se pidió centrar, solo centra.
            if opciones.quitar_fondo or not opciones.centrar:
                imagen = self.componedor.componer(imagen, mascara)
            if opciones.centrar:
                imagen = Centrador(ESPACIOS[opciones.espacio]).centrar(imagen, mascara)

        imagen = adaptador.adaptar(imagen, plataforma.ancho, plataforma.alto)
        imagen, amplio = self.redimensionador.redimensionar(imagen, plataforma.ancho, plataforma.alto)

        avisos = []
        if amplio:
            avisos.append(f"Tu foto es más chica de lo que pide {plataforma.nombre}. Puede verse un poco borrosa.")

        comprimida = self.compresor.comprimir(imagen, plataforma.formato, opciones.peso)
        if comprimida.aviso:
            avisos.append(comprimida.aviso)
        return ResultadoEdicion(
            contenido=comprimida.contenido, formato=plataforma.formato, tipo_mime=comprimida.tipo_mime,
            extension=comprimida.extension, ancho=plataforma.ancho, alto=plataforma.alto,
            peso_bytes=len(comprimida.contenido), calidad=comprimida.etiqueta, avisos=avisos,
        )
