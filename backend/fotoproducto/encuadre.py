"""Encuadre: lleva la foto a la proporción de la plataforma sin deformarla."""

from abc import ABC, abstractmethod
from typing import Callable

import cv2
import numpy as np

BLANCO = (255, 255, 255)



class Adaptador(ABC):
    """Lleva una imagen a la proporción ancho:alto del destino (no cambia el tamaño final)."""

    @abstractmethod
    def adaptar(self, imagen: np.ndarray, ancho: int, alto: int) -> np.ndarray:
        """Devuelve la imagen con la proporción ancho:alto pedida."""


class AgregarBordes(Adaptador):
    """Completa con blanco, centrado, lo que falta para llegar a la proporción."""

    def adaptar(self, imagen: np.ndarray, ancho: int, alto: int) -> np.ndarray:
        alto_i, ancho_i = imagen.shape[:2]
        # Una de las dos medidas se mantiene y la otra crece lo necesario.
        nuevo_ancho = max(ancho_i, round(alto_i * ancho / alto))
        nuevo_alto = max(alto_i, round(ancho_i * alto / ancho))
        arriba, izquierda = (nuevo_alto - alto_i) // 2, (nuevo_ancho - ancho_i) // 2
        return cv2.copyMakeBorder(
            imagen, arriba, nuevo_alto - alto_i - arriba, izquierda, nuevo_ancho - ancho_i - izquierda,
            cv2.BORDER_CONSTANT, value=BLANCO,
        )


class Recortar(Adaptador):
    """Recorta lo que sobra, conservando la parte indicada por las posiciones.

    posicion_x y posicion_y van de 0 a 1: 0 conserva el lado izquierdo/superior, 0.5 centra y
    1 conserva el lado derecho/inferior. Solo tiene efecto la del eje donde sobra foto.
    """

    def __init__(self, posicion_x: float = 0.5, posicion_y: float = 0.5) -> None:
        self.posicion_x = min(max(posicion_x, 0.0), 1.0)
        self.posicion_y = min(max(posicion_y, 0.0), 1.0)

    def adaptar(self, imagen: np.ndarray, ancho: int, alto: int) -> np.ndarray:
        alto_i, ancho_i = imagen.shape[:2]
        nuevo_ancho = max(1, min(ancho_i, round(alto_i * ancho / alto)))
        nuevo_alto = max(1, min(alto_i, round(ancho_i * alto / ancho)))
        # Solo uno de los dos ejes tiene sobrante; en el otro el desplazamiento da 0.
        x0 = round((ancho_i - nuevo_ancho) * self.posicion_x)
        y0 = round((alto_i - nuevo_alto) * self.posicion_y)
        return imagen[y0:y0 + nuevo_alto, x0:x0 + nuevo_ancho].copy()


# Se elige por nombre sin if/elif: agregar un adaptador es agregar una entrada.
ADAPTADORES: dict[str, Callable[[float, float], Adaptador]] = {
    "bordes": lambda posicion_x, posicion_y: AgregarBordes(),
    "recortar": Recortar,
}
