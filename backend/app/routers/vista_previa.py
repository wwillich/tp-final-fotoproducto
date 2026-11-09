import json
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core import editor
from app.esquemas import Adaptacion
from app.uploads import read_upload
from fotoproducto import OpcionesEdicion, ResultadoEdicion

router = APIRouter(prefix="/api", tags=["vista previa"])


def encabezados(resultado: ResultadoEdicion) -> dict[str, str]:
    """Datos del resultado como headers (ASCII: los avisos van como JSON codificado en URL)."""
    headers = {
        "X-Ancho": str(resultado.ancho),
        "X-Alto": str(resultado.alto),
        "X-Peso-Bytes": str(resultado.peso_bytes),
        "X-Avisos": quote(json.dumps(resultado.avisos)),
    }
    if resultado.calidad:
        headers["X-Calidad"] = quote(resultado.calidad)
    return headers


@router.post(
    "/vista-previa",
    summary="Procesa la foto y devuelve la imagen resultante (no guarda nada)",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/webp": {}}, "description": "La imagen procesada."}},
)
async def vista_previa(
    archivo: UploadFile = File(..., description="La foto original."),
    plataforma: str = Form(..., description="Clave de la plataforma (ver GET /api/plataformas)."),
    adaptacion: Adaptacion = Form("bordes", description="Qué hacer si la foto no entra en el formato."),
    posicion_x: float = Form(0.5, ge=0, le=1, description="Al recortar: 0 conserva la izquierda, 1 la derecha."),
    posicion_y: float = Form(0.5, ge=0, le=1, description="Al recortar: 0 conserva la parte de arriba, 1 la de abajo."),
):
    subida = await read_upload(archivo)
    opciones = OpcionesEdicion(plataforma=plataforma, adaptacion=adaptacion,
                               posicion_x=posicion_x, posicion_y=posicion_y)
    resultado = await run_in_threadpool(editor.procesar, subida.photo.image, opciones)
    return Response(resultado.contenido, media_type=resultado.tipo_mime, headers=encabezados(resultado))
