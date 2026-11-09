"""Instancias únicas del core y del repositorio que comparten los routers."""

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.repositorio import RepositorioTrabajos
from app.uploads import Upload, read_upload
from fotoproducto import CatalogoPlataformas, EditorFotoProducto, OpcionesEdicion, ResultadoEdicion

catalogo = CatalogoPlataformas()
editor = EditorFotoProducto(catalogo)
repositorio = RepositorioTrabajos()


async def procesar_subida(archivo: UploadFile, opciones: OpcionesEdicion,
                          marcas: UploadFile | None = None) -> tuple[Upload, ResultadoEdicion]:
    """Valida la foto (y las marcas, si vienen) y la procesa en un hilo, para no frenar al servidor."""
    subida = await read_upload(archivo)
    imagen_marcas = (await read_upload(marcas)).photo.image if marcas is not None else None
    resultado = await run_in_threadpool(editor.procesar, subida.photo.image, opciones, imagen_marcas)
    return subida, resultado
