"""Plataformas donde se puede publicar."""

from fastapi import APIRouter

from app.core import catalogo
from app.esquemas import PlataformaOut
from fotoproducto import Plataforma

router = APIRouter(prefix="/api", tags=["plataformas"])


@router.get("/plataformas", response_model=list[PlataformaOut], summary="Plataformas donde se puede publicar")
def listar_plataformas() -> list[Plataforma]:
    """Devuelve el catálogo de plataformas, con el tamaño y el formato de cada una."""
    return catalogo.listar()
