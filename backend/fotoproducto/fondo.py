"""Quitar el fondo: grabCut a partir de un contorno (automático o dibujado) y la foto sobre fondo blanco."""

import cv2
import numpy as np

from fotoproducto.exceptions import ContornoInvalido, ProductoNoEncontrado


def _impar(valor: int) -> int:
    """Tamaño de kernel válido para OpenCV: impar y al menos 1."""
    return max(1, valor) | 1


class QuitadorFondo:
    """Separa el producto del fondo con cv2.grabCut.

    Parte de un contorno aproximado: una zona que encierra el producto. Si no se da, usa una
    elipse centrada. Alrededor del borde del contorno deja una banda "dudosa" donde grabCut
    decide; el centro es producto seguro y lo que está lejos afuera es fondo seguro.

    Trabaja sobre una copia reducida (lado mayor `lado_trabajo`) para que sea rápido con fotos
    grandes, y devuelve la máscara al tamaño original.
    """

    def __init__(self, lado_trabajo: int = 640, banda: float = 0.03, iteraciones: int = 5,
                 tamano_elemento: int = 7, area_minima: float = 0.005,
                 fraccion_elipse: float = 0.7, fraccion_nucleo: float = 0.5,
                 suavizado_borde: float = 0.03, cierre_borde: float = 0.12,
                 banda_contorno: float = 0.012, fraccion_nucleo_contorno: float = 0.8) -> None:
        self.lado_trabajo = lado_trabajo      # px del lado mayor de la copia de trabajo
        self.banda = banda                    # ancho de la banda dudosa, fracción del lado mayor
        self.iteraciones = iteraciones        # pasadas de grabCut
        self.tamano_elemento = tamano_elemento  # elemento estructurante de la limpieza morfológica
        self.area_minima = area_minima        # fracción mínima de la foto que debe ocupar el producto
        self.fraccion_elipse = fraccion_elipse  # tamaño de la elipse automática respecto de la foto
        self.fraccion_nucleo = fraccion_nucleo  # qué parte (del centro) del contorno se da por producto seguro
        self.suavizado_borde = suavizado_borde  # desenfoque que redondea el borde, fracción del lado mayor
        self.banda_contorno = banda_contorno    # banda dudosa cuando el usuario dibujó el contorno
        self.fraccion_nucleo_contorno = fraccion_nucleo_contorno  # núcleo seguro cuando hay contorno del usuario
        self.cierre_borde = cierre_borde        # muescas del borde que se rellenan, fracción del lado mayor

    def mascara(self, imagen: np.ndarray, contorno: np.ndarray | None = None) -> np.ndarray:
        """Máscara uint8 (255 = producto, 0 = fondo) del tamaño de la imagen.

        `contorno` es una imagen donde lo claro (>127) es la zona que encierra el producto.
        Lanza ContornoInvalido si no encierra nada (o encierra toda la foto) y
        ProductoNoEncontrado si el producto resulta vacío o casi vacío.
        """
        alto, ancho = imagen.shape[:2]
        escala = min(1.0, self.lado_trabajo / max(alto, ancho))
        tamano = (round(ancho * escala), round(alto * escala))
        trabajo = cv2.resize(imagen, tamano, interpolation=cv2.INTER_AREA) if escala < 1.0 else imagen

        interior = self._interior(contorno, tamano)
        mascara = np.where(self._grabcut(trabajo, interior, contorno is not None), 255, 0).astype(np.uint8)
        mascara = self._suavizar_borde(self._limpiar(mascara))

        if np.count_nonzero(mascara) < self.area_minima * mascara.size:
            raise ProductoNoEncontrado(
                "No pudimos separar el producto. Probá marcar el contorno rodeándolo más de cerca.")
        if escala < 1.0:
            mascara = cv2.resize(mascara, (ancho, alto), interpolation=cv2.INTER_LINEAR)
            mascara = np.where(mascara > 127, 255, 0).astype(np.uint8)
        return mascara

    def _interior(self, contorno: np.ndarray | None, tamano: tuple[int, int]) -> np.ndarray:
        """Zona aproximada del producto (255 adentro) del tamaño de trabajo."""
        ancho, alto = tamano
        if contorno is None:
            interior = np.zeros((alto, ancho), np.uint8)
            ejes = (round(self.fraccion_elipse * ancho / 2), round(self.fraccion_elipse * alto / 2))
            cv2.ellipse(interior, (ancho // 2, alto // 2), ejes, 0, 0, 360, 255, -1)
            return interior
        if contorno.ndim == 3:
            contorno = cv2.cvtColor(contorno, cv2.COLOR_BGR2GRAY)
        # Es una zona, no un color: sin interpolar.
        contorno = cv2.resize(contorno, (ancho, alto), interpolation=cv2.INTER_NEAREST)
        interior = np.where(contorno > 127, 255, 0).astype(np.uint8)
        cantidad = np.count_nonzero(interior)
        if cantidad == 0 or cantidad == interior.size:
            raise ContornoInvalido(
                "El contorno no encierra ninguna zona de la foto. Dibujalo de nuevo rodeando el producto.")
        return interior

    def _grabcut(self, imagen: np.ndarray, interior: np.ndarray, guiado: bool) -> np.ndarray:
        """Corre grabCut y devuelve un booleano: True donde queda producto.

        Con un contorno del usuario (`guiado`) se confía más en él: banda dudosa más angosta y
        núcleo seguro más grande, así el borde sigue la línea dibujada y no se "come" el producto.
        """
        lado = max(interior.shape)
        k = _impar(round((self.banda_contorno if guiado else self.banda) * lado))
        fraccion_nucleo = self.fraccion_nucleo_contorno if guiado else self.fraccion_nucleo
        elemento = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        etiquetas = np.full(interior.shape, cv2.GC_BGD, np.uint8)
        etiquetas[cv2.dilate(interior, elemento) > 0] = cv2.GC_PR_BGD
        etiquetas[interior > 0] = cv2.GC_PR_FGD
        # El "producto seguro" es solo el centro del contorno: si fuera todo el interior, un contorno
        # holgado dejaría pedazos de fondo fijos como producto. El tamaño sale del área (≈ radio equivalente).
        radio = np.sqrt(np.count_nonzero(interior) / np.pi)
        diametro = _impar(round(fraccion_nucleo * 2 * radio))
        nucleo = cv2.erode(interior, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diametro, diametro)))
        if not nucleo.any():
            nucleo = cv2.erode(interior, elemento)  # contorno muy alargado: se usa el recorte fino
        etiquetas[nucleo > 0] = cv2.GC_FGD
        if not (etiquetas == cv2.GC_FGD).any():
            etiquetas[interior > 0] = cv2.GC_FGD  # contorno más angosto que la banda: todo es producto seguro
        modelo_fondo = np.zeros((1, 65), np.float64)
        modelo_producto = np.zeros((1, 65), np.float64)
        cv2.grabCut(imagen, etiquetas, None, modelo_fondo, modelo_producto,
                    self.iteraciones, cv2.GC_INIT_WITH_MASK)
        return (etiquetas == cv2.GC_FGD) | (etiquetas == cv2.GC_PR_FGD)

    def _suavizar_borde(self, mascara: np.ndarray) -> np.ndarray:
        """Rellena las muescas y redondea los dientes del borde: cierra, desenfoca y vuelve a binarizar."""
        lado = max(mascara.shape)
        cierre = _impar(round(self.cierre_borde * lado))
        # Con fondo negro alrededor: sin ese marco, cerrar arrastra el producto hasta el borde de la foto
        # (la erosión no cuenta lo que está fuera de la imagen).
        marco = cierre
        mascara = cv2.copyMakeBorder(mascara, marco, marco, marco, marco, cv2.BORDER_CONSTANT, value=0)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE,
                                   cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cierre, cierre)))
        mascara = mascara[marco:-marco, marco:-marco]
        k = _impar(round(self.suavizado_borde * lado))
        suave = cv2.GaussianBlur(mascara, (k, k), 0)
        return np.where(suave > 127, 255, 0).astype(np.uint8)

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
