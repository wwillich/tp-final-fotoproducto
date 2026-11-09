from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR, MEDIA_URL, STORAGE_DIR
from app.errors import register_exception_handlers
from app.routers import plataformas, trabajos, vista_previa


@asynccontextmanager
async def lifespan(app: FastAPI):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Foto de producto — TP final",
    description="API que deja la foto casera de un producto lista para publicar en una tienda online o red social.",
    version="0.1.0",
    lifespan=lifespan,
)

# Permite abrir el frontend desde otro origen (por ejemplo Live Server en :5500).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Ancho", "X-Alto", "X-Peso-Bytes", "X-Calidad", "X-Avisos"],
)


@app.get("/api/health", tags=["sistema"], summary="Estado del servidor")
def health():
    return {"status": "ok"}


# Excepciones de dominio (core y API) → respuestas {"detail": {"code", "message"}}.
register_exception_handlers(app)

app.include_router(plataformas.router)
app.include_router(vista_previa.router)
app.include_router(trabajos.router)


# Archivos guardados en disco (originales y resultados).
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL, StaticFiles(directory=STORAGE_DIR), name="media")

# Frontend (va al final porque captura "/").
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
