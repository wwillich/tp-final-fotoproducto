"""Contrato de entrada/salida de la API."""

from datetime import datetime
from typing import Any, Literal

from fastapi import Form
from pydantic import BaseModel

from fotoproducto import OpcionesEdicion

# Deben coincidir con el core (claves de ADAPTADORES y de Compresor.perfiles); un test lo verifica.
Adaptacion = Literal["bordes", "recortar"]
Peso = Literal["liviano", "normal", "maxima"]
Espacio = Literal["poco", "normal", "mucho"]
NivelNitidez = Literal["nada", "poco", "mucho"]


CONTORNO_AYUDA = ("Opcional. Imagen PNG donde lo blanco es la zona que rodea el producto (el resto, transparente "
                  "o negro). Sirve de guía para quitar el fondo o centrar; si no viene, el producto se detecta solo. "
                  "Si viene sin pedir centrar ni quitar el fondo, se quita el fondo.")


class PlataformaOut(BaseModel):
    """Una plataforma donde se puede publicar, con el tamaño y el formato que pide."""

    clave: str
    nombre: str
    ancho: int
    alto: int
    formato: str


class TrabajoOut(BaseModel):
    """Un trabajo guardado: dónde están sus archivos y con qué opciones se hizo."""

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
    posicion_y: float = Form(0.5, ge=0, le=1,
                             description="Al recortar: 0 conserva la parte de arriba, 1 la de abajo."),
    peso: Peso = Form("normal", description="Peso del archivo: liviano (hasta 200 KB), "
                                            "normal (hasta 500 KB) o maxima calidad."),
    quitar_fondo: bool = Form(False, description="Dejar el producto sobre fondo blanco."),
    centrar: bool = Form(False, description="Centrar el producto en la foto (con o sin quitar el fondo)."),
    espacio: Espacio = Form("normal", description="Espacio alrededor del producto al centrarlo."),
    brillo: float = Form(0, ge=-100, le=100, description="De -100 (más oscuro) a 100 (más claro). 0 no cambia nada."),
    contraste: float = Form(0, ge=-100, le=100,
                            description="De -100 (más apagado) a 100 (más marcado). 0 no cambia nada."),
    aclarar_oscuras: float = Form(0, ge=0, le=1,
                                  description="Cuánto aclarar las zonas oscuras, de 0 (nada) a 1 (mucho)."),
    colores_naturales: bool = Form(False, description="Corrige el tono amarillento o azulado de la luz."),
    nitidez: NivelNitidez = Form("nada", description="Realce de los bordes, aplicado al tamaño final."),
) -> OpcionesEdicion:
    """Dependencia que arma las opciones de edición a partir de los campos del formulario."""
    return OpcionesEdicion(plataforma=plataforma, adaptacion=adaptacion, posicion_x=posicion_x,
                           posicion_y=posicion_y, peso=peso, quitar_fondo=quitar_fondo,
                           centrar=centrar, espacio=espacio, brillo=brillo, contraste=contraste,
                           aclarar_oscuras=aclarar_oscuras, colores_naturales=colores_naturales,
                           nitidez=nitidez)
