"""Compresión: codifica la imagen final en el formato de la plataforma y controla su peso."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

from fotoproducto.exceptions import ErrorFotoProducto

KB = 1024

AVISO_PESO = "No se pudo bajar del peso elegido sin arruinar la foto. Se guardó con la mejor calidad posible."


class Codificador(ABC):
    """Convierte una imagen en los bytes de un formato, con una calidad de 1 a 100."""

    extension: str  # con punto, como la pide cv2.imencode
    tipo_mime: str

    @abstractmethod
    def parametros(self, calidad: int) -> list[int]:
        """Parámetros de cv2.imencode para esa calidad."""

    def codificar(self, imagen: np.ndarray, calidad: int) -> bytes:
        """Devuelve la imagen codificada."""
        ok, buffer = cv2.imencode(self.extension, imagen, self.parametros(calidad))
        if not ok:
            raise ErrorFotoProducto("No se pudo guardar la imagen en el formato pedido.")
        return buffer.tobytes()


class CodificadorJPEG(Codificador):
    extension = ".jpg"
    tipo_mime = "image/jpeg"

    def parametros(self, calidad: int) -> list[int]:
        return [cv2.IMWRITE_JPEG_QUALITY, calidad]


class CodificadorWebP(Codificador):
    extension = ".webp"
    tipo_mime = "image/webp"

    def parametros(self, calidad: int) -> list[int]:
        return [cv2.IMWRITE_WEBP_QUALITY, calidad]


class CodificadorPNG(Codificador):
    """PNG no pierde calidad: la "calidad" solo elige cuánto se comprime (más calidad = menos compresión)."""

    extension = ".png"
    tipo_mime = "image/png"

    def parametros(self, calidad: int) -> list[int]:
        return [cv2.IMWRITE_PNG_COMPRESSION, min(9, max(0, round((100 - calidad) * 9 / 100)))]


# Se elige por nombre de formato sin if/elif: agregar un formato es agregar una entrada.
CODIFICADORES: dict[str, Codificador] = {
    "JPEG": CodificadorJPEG(),
    "WEBP": CodificadorWebP(),
    "PNG": CodificadorPNG(),
}


@dataclass
class ResultadoCompresion:
    """Imagen codificada, la calidad usada y qué tan fiel quedó respecto de la original."""

    contenido: bytes
    tipo_mime: str
    extension: str
    calidad: int          # número de 1 a 100 con el que se codificó
    etiqueta: str         # "excelente", "muy buena", "buena" o "aceptable"
    aviso: str | None = None


class Compresor:
    """Busca la mayor calidad que entra en el peso elegido y la traduce a una etiqueta.

    Perfiles: límite de peso en bytes, o None si no hay límite (se usa la calidad máxima).
    """

    def __init__(
        self,
        perfiles: dict[str, int | None] | None = None,
        calidad_minima: int = 30,
        calidad_maxima: int = 95,
        umbrales_psnr: tuple[tuple[float, str], ...] = ((40.0, "excelente"), (35.0, "muy buena"), (30.0, "buena")),
        etiqueta_minima: str = "aceptable",
    ) -> None:
        self.perfiles = perfiles or {"liviano": 200 * KB, "normal": 500 * KB, "maxima": None}
        self.calidad_minima = calidad_minima
        self.calidad_maxima = calidad_maxima
        self.umbrales_psnr = umbrales_psnr
        self.etiqueta_minima = etiqueta_minima

    def comprimir(self, imagen: np.ndarray, formato: str, perfil: str) -> ResultadoCompresion:
        """Codifica `imagen` en `formato` respetando el límite de peso del `perfil`."""
        codificador = CODIFICADORES[formato]
        limite = self.perfiles[perfil]
        aviso = None

        if limite is None:
            calidad = self.calidad_maxima
            contenido = codificador.codificar(imagen, calidad)
        else:
            # Búsqueda binaria de la mayor calidad cuyo archivo entra en el límite.
            mejor = None
            bajo, alto = self.calidad_minima, self.calidad_maxima
            while bajo <= alto:
                medio = (bajo + alto) // 2
                candidato = codificador.codificar(imagen, medio)
                if len(candidato) <= limite:
                    mejor = (medio, candidato)
                    bajo = medio + 1
                else:
                    alto = medio - 1
            if mejor is None:  # ni con la calidad mínima entra: se entrega la mejor posible
                mejor = (self.calidad_minima, codificador.codificar(imagen, self.calidad_minima))
                aviso = AVISO_PESO
            calidad, contenido = mejor

        return ResultadoCompresion(
            contenido=contenido, tipo_mime=codificador.tipo_mime, extension=codificador.extension,
            calidad=calidad, etiqueta=self._etiqueta_de(imagen, contenido), aviso=aviso,
        )

    def etiquetar(self, psnr: float) -> str:
        """Traduce un PSNR (en dB) a una etiqueta de calidad en palabras."""
        for umbral, etiqueta in self.umbrales_psnr:
            if psnr >= umbral:
                return etiqueta
        return self.etiqueta_minima

    def _etiqueta_de(self, imagen: np.ndarray, contenido: bytes) -> str:
        """Mide la pérdida (imagen decodificada vs. sin comprimir) con cv2.PSNR."""
        decodificada = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)
        if np.array_equal(decodificada, imagen):  # sin pérdida (cv2.PSNR da 0 si son idénticas)
            return self.umbrales_psnr[0][1]
        return self.etiquetar(cv2.PSNR(imagen, decodificada))
