"""
Traducción de excepciones a respuestas HTTP.

Todo error sale de la API con el mismo formato:

    {"detail": {"code": "INVALID_FILE", "message": "..."}}

Los endpoints no llevan try/except: dejan subir las excepciones y estos
manejadores responden.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fotoproducto import ErrorFotoProducto, InvalidImage, PlataformaDesconocida


class ApiError(Exception):
    """Un error de la API misma (no del core), con su estado y su código."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class TrabajoNoEncontrado(ApiError):
    """No hay un trabajo guardado con ese id."""

    def __init__(self, id: str) -> None:
        super().__init__(404, "TRABAJO_NO_ENCONTRADO", f"No existe un trabajo guardado con id {id!r}.")


# Excepciones del core → (estado HTTP, código). Las subclases heredan la entrada de su padre.
CORE_ERRORS: dict[type[ErrorFotoProducto], tuple[int, str]] = {
    InvalidImage: (400, "INVALID_FILE"),
    PlataformaDesconocida: (422, "PLATAFORMA_DESCONOCIDA"),
    ErrorFotoProducto: (400, "ERROR_FOTOPRODUCTO"),
}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message}})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(ErrorFotoProducto)
    async def handle_core_error(request: Request, exc: ErrorFotoProducto) -> JSONResponse:
        for exc_type in type(exc).__mro__:
            if exc_type in CORE_ERRORS:
                status, code = CORE_ERRORS[exc_type]
                return error_response(status, code, str(exc))
        return error_response(400, "ERROR_FOTOPRODUCTO", str(exc))  # pragma: no cover
