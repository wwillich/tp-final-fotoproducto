"""Contrato de entrada/salida de la API."""

from typing import Literal

from pydantic import BaseModel

# Debe coincidir con las claves de fotoproducto.encuadre.ADAPTADORES; un test lo verifica.
Adaptacion = Literal["bordes", "recortar"]


class PlataformaOut(BaseModel):
    clave: str
    nombre: str
    ancho: int
    alto: int
    formato: str
