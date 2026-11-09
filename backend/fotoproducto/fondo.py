"""Quitar el fondo: del trazo del usuario a una máscara del producto y a la foto sobre fondo blanco."""

import cv2
import numpy as np

from fotoproducto.exceptions import MarcasInsuficientes, ProductoNoEncontrado

# Etiquetas de los marcadores de cv2.watershed (0 = sin marcar, -1 lo usa el algoritmo en los bordes).
MARCA_FONDO = 1
MARCA_PRODUCTO = 2


def _impar(valor: int) -> int:
    """Tamaño de kernel válido para OpenCV: impar y al menos 1."""
    return max(1, valor) | 1


class InterpretadorMarcas:
    """Convierte la imagen de marcas del usuario en la matriz de marcadores de cv2.watershed.

    En la imagen de marcas, los trazos verdes son el producto y los rojos el fondo; lo demás
    (negro o transparente) no está marcado. Se compara un canal contra los otros dos con un
    margen, así no importa que los bordes del pincel salgan un poco mezclados.
    """

    def __init__(self, margen_color: int = 64) -> None:
        self.margen_color = margen_color

    def interpretar(self, marcas: np.ndarray, forma: tuple[int, int]) -> np.ndarray:
        """Devuelve marcadores int32 del tamaño (alto, ancho) de la foto.

        Lanza MarcasInsuficientes si falta alguna de las dos clases.
        """
        alto, ancho = forma
        if marcas.shape[:2] != (alto, ancho):
            # Son etiquetas, no colores: sin interpolar.
            marcas = cv2.resize(marcas, (ancho, alto), interpolation=cv2.INTER_NEAREST)
        azul, verde, rojo = (canal.astype(np.int16) for canal in cv2.split(marcas))
        m = self.margen_color
        producto = (verde > rojo + m) & (verde > azul + m)
        fondo = (rojo > verde + m) & (rojo > azul + m)
        if not producto.any() or not fondo.any():
            raise MarcasInsuficientes("Marcá al menos una parte del producto (verde) y una del fondo (rojo).")

        marcadores = np.zeros((alto, ancho), np.int32)
        marcadores[fondo] = MARCA_FONDO
        marcadores[producto] = MARCA_PRODUCTO
        return marcadores


class QuitadorFondo:
    """Separa el producto del fondo con cv2.watershed a partir de los marcadores.

    Trabaja sobre una copia reducida (lado mayor `lado_trabajo`) para que sea rápido con fotos
    grandes, y devuelve la máscara al tamaño original.
    """

    def __init__(self, lado_trabajo: int = 1600, suavizado: int = 5,
                 tamano_elemento: int = 7, area_minima: float = 0.005) -> None:
        self.lado_trabajo = lado_trabajo      # px del lado mayor de la copia de trabajo
        self.suavizado = suavizado            # kernel del desenfoque previo (reduce el ruido); 1 = sin desenfoque
        self.tamano_elemento = tamano_elemento  # elemento estructurante de la limpieza morfológica
        self.area_minima = area_minima        # fracción mínima de la foto que debe ocupar el producto

    def mascara(self, imagen: np.ndarray, marcadores: np.ndarray) -> np.ndarray:
        """Máscara uint8 (255 = producto, 0 = fondo) del tamaño de la imagen.

        Lanza ProductoNoEncontrado si el producto queda vacío o casi vacío.
        """
        alto, ancho = imagen.shape[:2]
        escala = min(1.0, self.lado_trabajo / max(alto, ancho))
        if escala < 1.0:
            tamano = (round(ancho * escala), round(alto * escala))
            trabajo = cv2.resize(imagen, tamano, interpolation=cv2.INTER_AREA)
            marcadores = self._reducir_marcadores(marcadores, tamano)
        else:
            trabajo, marcadores = imagen, marcadores.copy()  # watershed escribe sobre los marcadores

        if self.suavizado > 1:
            trabajo = cv2.GaussianBlur(trabajo, (_impar(self.suavizado),) * 2, 0)
        cv2.watershed(trabajo, marcadores)
        mascara = self._limpiar(np.where(marcadores == MARCA_PRODUCTO, 255, 0).astype(np.uint8))

        if np.count_nonzero(mascara) < self.area_minima * mascara.size:
            raise ProductoNoEncontrado(
                "No pudimos separar el producto. Probá marcar un poco más del producto y del fondo.")
        if escala < 1.0:
            mascara = cv2.resize(mascara, (ancho, alto), interpolation=cv2.INTER_LINEAR)
            mascara = np.where(mascara > 127, 255, 0).astype(np.uint8)
        return mascara

    @staticmethod
    def _reducir_marcadores(marcadores: np.ndarray, tamano: tuple[int, int]) -> np.ndarray:
        """Reduce los marcadores clase por clase con INTER_AREA para que un trazo fino no desaparezca."""
        reducidos = np.zeros(tamano[::-1], np.int32)
        for etiqueta in (MARCA_FONDO, MARCA_PRODUCTO):
            clase = ((marcadores == etiqueta) * np.uint8(255)).astype(np.uint8)
            reducidos[cv2.resize(clase, tamano, interpolation=cv2.INTER_AREA) > 0] = etiqueta
        return reducidos

    def _limpiar(self, mascara: np.ndarray) -> np.ndarray:
        """Cierra huecos, saca manchas sueltas y se queda con la componente más grande."""
        elemento = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_impar(self.tamano_elemento),) * 2)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, elemento)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, elemento)
        cantidad, etiquetas = cv2.connectedComponents(mascara)
        if cantidad <= 1:
            return mascara  # vacía
        areas = np.bincount(etiquetas.ravel())[1:]  # sin la etiqueta 0 (el fondo)
        return np.where(etiquetas == np.argmax(areas) + 1, 255, 0).astype(np.uint8)


class ComponedorFondoBlanco:
    """Pone el producto sobre blanco con el borde suavizado, para que no se vea recortado con tijera."""

    def __init__(self, radio_relativo: float = 0.002) -> None:
        self.radio_relativo = radio_relativo  # ancho del borde suave como fracción del lado mayor

    def componer(self, imagen: np.ndarray, mascara: np.ndarray) -> np.ndarray:
        """Devuelve la imagen con todo lo que no es producto en blanco."""
        radio = _impar(round(self.radio_relativo * max(imagen.shape[:2])))
        # Se encoge la máscara tanto como se extiende el suavizado: así el borde suave cae dentro
        # del producto y no deja un halo del color del fondo original.
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radio, radio))
        alfa = cv2.GaussianBlur(cv2.erode(mascara, nucleo), (radio, radio), 0).astype(np.float32) / 255
        alfa = alfa[..., None]
        return np.rint(imagen * alfa + 255 * (1 - alfa)).astype(np.uint8)
