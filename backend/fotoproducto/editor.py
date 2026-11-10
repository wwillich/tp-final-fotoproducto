"""Editor: orquesta las etapas del procesamiento en el orden correcto."""

from dataclasses import dataclass, field

import numpy as np

from fotoproducto.ajustes import (
    Ajuste, AclararZonasOscuras, BrilloContraste, ColoresNaturales, NIVELES_NITIDEZ, Nitidez,
)
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
    brillo: float = 0           # de -100 (más oscuro) a 100 (más claro)
    contraste: float = 0        # de -100 (más apagado) a 100 (más marcado)
    aclarar_oscuras: float = 0  # de 0 (nada) a 1 (mucho)
    colores_naturales: bool = False  # corrige el tono amarillento o azulado de la luz
    nitidez: str = "nada"       # clave de NIVELES_NITIDEZ; se aplica después de cambiar el tamaño


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

    @staticmethod
    def ajustes(opciones: OpcionesEdicion) -> list[Ajuste]:
        """Los ajustes de luz y color en el orden en que se aplican: primero el color, después la luz."""
        return [
            ColoresNaturales(opciones.colores_naturales),
            AclararZonasOscuras(opciones.aclarar_oscuras),
            BrilloContraste(opciones.brillo, opciones.contraste),
        ]

    def procesar(self, imagen: np.ndarray, opciones: OpcionesEdicion,
                 contorno: np.ndarray | None = None) -> ResultadoEdicion:
        """Quita el fondo (si se pidió), adapta a la proporción de la plataforma, cambia al
        tamaño exacto y comprime.

        `contorno` es opcional: una imagen donde lo claro encierra el producto. Si se da,
        el fondo se quita aunque `opciones.quitar_fondo` sea False.
        """
        plataforma = self.catalogo.obtener(opciones.plataforma)
        adaptador = ADAPTADORES[opciones.adaptacion](opciones.posicion_x, opciones.posicion_y)

        # La máscara sirve para las dos cosas: saber dónde está el producto (centrar) y qué es fondo (quitarlo).
        # Se calcula con la foto original, antes de tocar la luz y el color.
        mascara = None
        if opciones.quitar_fondo or opciones.centrar or contorno is not None:
            mascara = self.quitador.mascara(imagen, contorno)

        # Luz y color van antes del fondo blanco: así el blanco no se tiñe ni se agrisa.
        for ajuste in self.ajustes(opciones):
            imagen = ajuste.aplicar(imagen)

        if mascara is not None:
            # Un contorno solo, sin pedir nada más, quita el fondo; si se pidió centrar, solo centra.
            if opciones.quitar_fondo or not opciones.centrar:
                imagen = self.componedor.componer(imagen, mascara)
            if opciones.centrar:
                imagen = Centrador(ESPACIOS[opciones.espacio]).centrar(imagen, mascara)

        imagen = adaptador.adaptar(imagen, plataforma.ancho, plataforma.alto)
        imagen, amplio = self.redimensionador.redimensionar(imagen, plataforma.ancho, plataforma.alto)
        # La nitidez va después de cambiar el tamaño: reducir es lo que le quita nitidez a la foto.
        imagen = Nitidez(NIVELES_NITIDEZ[opciones.nitidez]).aplicar(imagen)

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
