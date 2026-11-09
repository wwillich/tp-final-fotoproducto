import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile

from app.core import procesar_subida
from app.esquemas import MARCAS_AYUDA, opciones_desde_form
from fotoproducto import OpcionesEdicion, ResultadoEdicion

router = APIRouter(prefix="/api", tags=["vista previa"])


def encabezados(resultado: ResultadoEdicion) -> dict[str, str]:
    """Datos del resultado como headers (ASCII: calidad y avisos van codificados en URL)."""
    return {
        "X-Ancho": str(resultado.ancho),
        "X-Alto": str(resultado.alto),
        "X-Peso-Bytes": str(resultado.peso_bytes),
        "X-Calidad": quote(resultado.calidad),
        "X-Avisos": quote(json.dumps(resultado.avisos)),
    }


@router.post(
    "/vista-previa",
    summary="Procesa la foto y devuelve la imagen resultante (no guarda nada)",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/webp": {}}, "description": "La imagen procesada."}},
)
async def vista_previa(
    archivo: UploadFile = File(..., description="La foto original."),
    marcas: UploadFile | None = File(None, description=MARCAS_AYUDA),
    opciones: OpcionesEdicion = Depends(opciones_desde_form),
):
    _, resultado = await procesar_subida(archivo, opciones, marcas)
    return Response(resultado.contenido, media_type=resultado.tipo_mime, headers=encabezados(resultado))
