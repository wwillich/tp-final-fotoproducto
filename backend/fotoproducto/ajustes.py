"""Ajustes de luz y color. Cada uno, con su valor neutro, devuelve la imagen sin tocarla."""

from abc import ABC, abstractmethod

import cv2
import numpy as np


class Ajuste(ABC):
    """Una corrección de la imagen: recibe una imagen BGR uint8 y devuelve otra del mismo tamaño."""

    @abstractmethod
    def aplicar(self, imagen: np.ndarray) -> np.ndarray:
        """Devuelve la imagen corregida (o la misma, si el ajuste está en su valor neutro)."""


class BrilloContraste(Ajuste):
    """g = α·(f − 128) + 128 + β: el contraste gira los valores alrededor del gris medio y el brillo los desplaza.

    `brillo` y `contraste` van de −100 a 100; 0 es neutro. Se calcula en float y se recorta a 0..255
    (cv2.convertScaleAbs devuelve el valor absoluto: un brillo negativo daría vuelta los píxeles oscuros).
    """

    PIVOTE = 128  # gris medio sobre el que gira el contraste

    def __init__(self, brillo: float = 0, contraste: float = 0) -> None:
        self.brillo = brillo
        self.contraste = contraste

    def aplicar(self, imagen: np.ndarray) -> np.ndarray:
        if self.brillo == 0 and self.contraste == 0:
            return imagen
        alfa = max(0.0, 1 + self.contraste / 100)
        beta = self.PIVOTE * (1 - alfa) + self.brillo
        return np.clip(np.rint(alfa * imagen.astype(np.float32) + beta), 0, 255).astype(np.uint8)


class AclararZonasOscuras(Ajuste):
    """Levanta el detalle de las sombras: CLAHE sobre la luminosidad (canal L de Lab), mezclado según `intensidad`.

    `intensidad` va de 0 (neutro) a 1. CLAHE equilibra el contraste por zonas, así que lo oscuro gana
    luz sin quemar lo que ya estaba claro.
    """

    def __init__(self, intensidad: float = 0, limite_contraste: float = 4.0, grilla: int = 8) -> None:
        self.intensidad = min(max(intensidad, 0.0), 1.0)
        self.limite_contraste = limite_contraste  # clipLimit de CLAHE con intensidad 1
        self.grilla = grilla                      # la imagen se divide en grilla × grilla zonas

    def aplicar(self, imagen: np.ndarray) -> np.ndarray:
        if self.intensidad == 0:
            return imagen
        luz, a, b = cv2.split(cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB))
        clahe = cv2.createCLAHE(clipLimit=1 + (self.limite_contraste - 1) * self.intensidad,
                                tileGridSize=(self.grilla, self.grilla))
        mezcla = luz + self.intensidad * (clahe.apply(luz).astype(np.float32) - luz)
        luz = np.clip(np.rint(mezcla), 0, 255).astype(np.uint8)
        return cv2.cvtColor(cv2.merge([luz, a, b]), cv2.COLOR_LAB2BGR)


class ColoresNaturales(Ajuste):
    """Corrige el tono amarillento o azulado de la luz: estira cada canal para que su valor casi máximo llegue a 255.

    El "casi máximo" es el percentil `percentil` del canal, hallado con el histograma acumulado
    (np.percentile no está entre las funciones del curso). Si la luz es cálida, el azul es el canal
    que menos llega a 255 y es el que más se estira.
    """

    def __init__(self, activo: bool = False, percentil: float = 0.99, ganancia_maxima: float = 2.0) -> None:
        self.activo = activo
        self.percentil = percentil              # fracción de píxeles que queda por debajo del "casi máximo"
        self.ganancia_maxima = ganancia_maxima  # tope del estiramiento, para no multiplicar el ruido de una foto muy oscura

    def aplicar(self, imagen: np.ndarray) -> np.ndarray:
        if not self.activo:
            return imagen
        canales = []
        for canal in cv2.split(imagen):
            histograma = cv2.calcHist([canal], [0], None, [256], [0, 256]).ravel()
            acumulado = np.cumsum(histograma) / canal.size
            casi_maximo = max(1, int(np.searchsorted(acumulado, self.percentil)))
            ganancia = min(255 / casi_maximo, self.ganancia_maxima)
            canales.append(np.clip(np.rint(canal.astype(np.float32) * ganancia), 0, 255).astype(np.uint8))
        return cv2.merge(canales)
