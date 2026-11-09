"""Editor: orquesta las etapas del procesamiento en el orden correcto."""

from dataclasses import dataclass, field

import cv2
import numpy as np

from fotoproducto.encuadre import ADAPTADORES
from fotoproducto.exceptions import ErrorFotoProducto
from fotoproducto.plataformas import CatalogoPlataformas
from fotoproducto.redimension import Redimensionador

# Codificación provisoria con calidad fija; F2 la reemplaza por el Compresor con perfiles de peso.
CALIDAD_FIJA = 90
CODIFICACION = {
    "JPEG": (".jpg", "image/jpeg", [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_FIJA]),
    "WEBP": (".webp", "image/webp", [cv2.IMWRITE_WEBP_QUALITY, CALIDAD_FIJA]),
}


@dataclass
class OpcionesEdicion:
    """Lo que el usuario eligió. Se irán sumando campos a medida que haya más etapas."""

    plataforma: str
    adaptacion: str = "bordes"  # clave de ADAPTADORES
    posicion_x: float = 0.5     # al recortar: 0 conserva la izquierda … 1 la derecha
    posicion_y: float = 0.5     # al recortar: 0 conserva la parte de arriba … 1 la de abajo


@dataclass
class ResultadoEdicion:
    """La imagen final ya codificada, con sus datos."""

    contenido: bytes
    formato: str
    tipo_mime: str
    ancho: int
    alto: int
    peso_bytes: int
    calidad: str | None = None  # etiqueta de calidad: la calcula el Compresor (F2)
    avisos: list[str] = field(default_factory=list)


class EditorFotoProducto:
    """Aplica las etapas de edición a una foto y devuelve el resultado listo para publicar."""

    def __init__(self, catalogo: CatalogoPlataformas | None = None,
                 redimensionador: Redimensionador | None = None) -> None:
        self.catalogo = catalogo or CatalogoPlataformas()
        self.redimensionador = redimensionador or Redimensionador()

    def procesar(self, imagen: np.ndarray, opciones: OpcionesEdicion) -> ResultadoEdicion:
        """Adapta a la proporción de la plataforma, cambia al tamaño exacto y codifica."""
        plataforma = self.catalogo.obtener(opciones.plataforma)
        adaptador = ADAPTADORES[opciones.adaptacion](opciones.posicion_x, opciones.posicion_y)

        imagen = adaptador.adaptar(imagen, plataforma.ancho, plataforma.alto)
        imagen, amplio = self.redimensionador.redimensionar(imagen, plataforma.ancho, plataforma.alto)

        avisos = []
        if amplio:
            avisos.append(f"Tu foto es más chica de lo que pide {plataforma.nombre}. Puede verse un poco borrosa.")

        extension, tipo_mime, parametros = CODIFICACION[plataforma.formato]
        ok, buffer = cv2.imencode(extension, imagen, parametros)
        if not ok:
            raise ErrorFotoProducto("No se pudo guardar la imagen en el formato pedido.")
        contenido = buffer.tobytes()
        return ResultadoEdicion(
            contenido=contenido, formato=plataforma.formato, tipo_mime=tipo_mime,
            ancho=plataforma.ancho, alto=plataforma.alto, peso_bytes=len(contenido), avisos=avisos,
        )
