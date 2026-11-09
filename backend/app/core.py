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
                          contorno: UploadFile | None = None) -> tuple[Upload, ResultadoEdicion]:
    """Valida la foto (y el contorno, si viene) y la procesa en un hilo, para no frenar al servidor."""
    subida = await read_upload(archivo)
    imagen_contorno = (await read_upload(contorno)).photo.image if contorno is not None else None
    resultado = await run_in_threadpool(editor.procesar, subida.photo.image, opciones, imagen_contorno)
    return subida, resultado
