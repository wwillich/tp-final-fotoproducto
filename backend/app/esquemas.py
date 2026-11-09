"""Contrato de entrada/salida de la API."""

from datetime import datetime
from typing import Any, Literal

from fastapi import Form
from pydantic import BaseModel

from fotoproducto import OpcionesEdicion

# Deben coincidir con el core (claves de ADAPTADORES y de Compresor.perfiles); un test lo verifica.
Adaptacion = Literal["bordes", "recortar"]
Peso = Literal["liviano", "normal", "maxima"]


CONTORNO_AYUDA = ("Opcional. Imagen PNG donde lo blanco es la zona que rodea el producto (el resto, transparente "
                  "o negro). Si viene, el fondo se quita usando esa zona como guía; si no, se detecta solo.")


class PlataformaOut(BaseModel):
    clave: str
    nombre: str
    ancho: int
    alto: int
    formato: str


class TrabajoOut(BaseModel):
    id: str
    nombre_original: str
    url: str
    url_original: str
    plataforma: str
    formato: str
    ancho: int
    alto: int
    peso_bytes: int
    calidad: str
    avisos: list[str]
    opciones: dict[str, Any]
    creado: datetime


def opciones_desde_form(
    plataforma: str = Form(..., description="Clave de la plataforma (ver GET /api/plataformas)."),
    adaptacion: Adaptacion = Form("bordes", description="Qué hacer si la foto no entra en el formato."),
    posicion_x: float = Form(0.5, ge=0, le=1, description="Al recortar: 0 conserva la izquierda, 1 la derecha."),
    posicion_y: float = Form(0.5, ge=0, le=1, description="Al recortar: 0 conserva la parte de arriba, 1 la de abajo."),
    peso: Peso = Form("normal", description="Peso del archivo: liviano (hasta 200 KB), normal (hasta 500 KB) o maxima calidad."),
    quitar_fondo: bool = Form(False, description="Dejar el producto sobre fondo blanco."),
) -> OpcionesEdicion:
    """Dependencia que arma las opciones de edición a partir de los campos del formulario."""
    return OpcionesEdicion(plataforma=plataforma, adaptacion=adaptacion, posicion_x=posicion_x,
                           posicion_y=posicion_y, peso=peso, quitar_fondo=quitar_fondo)
