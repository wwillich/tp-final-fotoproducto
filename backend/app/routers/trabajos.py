"""Trabajos guardados: crear (procesar y guardar), listar, ver y borrar."""

from fastapi import APIRouter, Depends, File, Response, UploadFile

from app.core import procesar_subida, repositorio
from app.esquemas import CONTORNO_AYUDA, TrabajoOut, opciones_desde_form
from fotoproducto import OpcionesEdicion

router = APIRouter(prefix="/api/trabajos", tags=["trabajos"])


@router.post("", status_code=201, response_model=TrabajoOut, summary="Procesa la foto y guarda el trabajo")
async def crear_trabajo(
    archivo: UploadFile = File(..., description="La foto original."),
    contorno: UploadFile | None = File(None, description=CONTORNO_AYUDA),
    opciones: OpcionesEdicion = Depends(opciones_desde_form),
) -> TrabajoOut:
    """Procesa la foto con las opciones elegidas y guarda el original y el resultado."""
    subida, resultado = await procesar_subida(archivo, opciones, contorno)
    return repositorio.guardar(subida, resultado, opciones)


@router.get("", response_model=list[TrabajoOut], summary="Trabajos guardados, el más nuevo primero")
def listar_trabajos() -> list[TrabajoOut]:
    """Devuelve todos los trabajos guardados."""
    return repositorio.listar()


@router.get("/{id}", response_model=TrabajoOut, summary="Un trabajo guardado")
def obtener_trabajo(id: str) -> TrabajoOut:
    """Devuelve un trabajo guardado; 404 si no existe."""
    return repositorio.obtener(id)


@router.delete("/{id}", status_code=204, summary="Borra el trabajo y todos sus archivos")
def borrar_trabajo(id: str) -> Response:
    """Borra el trabajo y sus archivos; 404 si no existe."""
    repositorio.borrar(id)
    return Response(status_code=204)
