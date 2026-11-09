"""Catálogo de plataformas de publicación (medidas y formato que pide cada una)."""

import json
from dataclasses import dataclass
from pathlib import Path

from fotoproducto.exceptions import PlataformaDesconocida

RUTA_CATALOGO = Path(__file__).with_name("plataformas.json")


@dataclass(frozen=True)
class Plataforma:
    """Una plataforma de publicación: tamaño exacto y formato de archivo."""

    clave: str
    nombre: str
    ancho: int
    alto: int
    formato: str  # "JPEG" o "WEBP"


class CatalogoPlataformas:
    """Plataformas disponibles, cargadas de un JSON: agregar una es editar el archivo."""

    def __init__(self, ruta: Path = RUTA_CATALOGO) -> None:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        self._plataformas = {d["clave"]: Plataforma(**d) for d in datos}

    def obtener(self, clave: str) -> Plataforma:
        """Devuelve la plataforma con esa clave o lanza PlataformaDesconocida."""
        try:
            return self._plataformas[clave]
        except KeyError:
            claves = ", ".join(self._plataformas)
            raise PlataformaDesconocida(
                f"No conocemos la plataforma {clave!r}. Elegí una de estas: {claves}."
            ) from None

    def listar(self) -> list[Plataforma]:
        """Todas las plataformas, en el orden del archivo."""
        return list(self._plataformas.values())
