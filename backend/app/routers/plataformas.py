from fastapi import APIRouter

from app.core import catalogo
from app.esquemas import PlataformaOut

router = APIRouter(prefix="/api", tags=["plataformas"])


@router.get("/plataformas", response_model=list[PlataformaOut], summary="Plataformas donde se puede publicar")
def listar_plataformas():
    return catalogo.listar()
