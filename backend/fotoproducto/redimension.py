"""Cambio de tamaño de la imagen."""

import cv2
import numpy as np


class Redimensionador:
    """Lleva la imagen al tamaño exacto eligiendo solo el método de interpolación.

    INTER_AREA al reducir (promedia los píxeles, evita el aliasing) e
    INTER_CUBIC al ampliar (suaviza mejor que el vecino más cercano o el bilineal).
    """

    def __init__(self, reduccion: int = cv2.INTER_AREA, ampliacion: int = cv2.INTER_CUBIC) -> None:
        self.reduccion = reduccion
        self.ampliacion = ampliacion

    def redimensionar(self, imagen: np.ndarray, ancho: int, alto: int) -> tuple[np.ndarray, bool]:
        """Devuelve (imagen del tamaño pedido, si hubo que ampliarla)."""
        amplia = ancho > imagen.shape[1] or alto > imagen.shape[0]
        metodo = self.ampliacion if amplia else self.reduccion
        return cv2.resize(imagen, (ancho, alto), interpolation=metodo), amplia
