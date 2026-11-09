# Foto de producto

TP final de Técnicas de Procesamiento Digital de Imágenes. App web local que deja la foto casera de un producto lista para publicar en una tienda online o red social.

> En construcción. El README completo se escribe al cierre del proyecto.

## Cómo correrlo

Requiere Python 3.10 o superior.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765
```

- Interfaz: http://localhost:8765
- Swagger: http://localhost:8765/docs
- Tests: `pytest -v` (desde `backend/`)
