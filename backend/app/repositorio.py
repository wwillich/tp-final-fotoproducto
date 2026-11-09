"""Almacenamiento en disco de los trabajos guardados.

Cada trabajo vive en su propia carpeta `STORAGE_DIR/<id>/` con tres archivos de nombre fijo:
`original.<ext>`, `resultado.<ext>` y `meta.json`. El nombre que puso el usuario a su archivo
solo se guarda dentro de meta.json: nunca se usa para nombrar nada en disco.
"""

import re
import shutil
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.config import MEDIA_URL, STORAGE_DIR
from app.errors import TrabajoNoEncontrado
from app.esquemas import TrabajoOut
from app.uploads import Upload
from fotoproducto import OpcionesEdicion, ResultadoEdicion

ID_VALIDO = re.compile(r"^[0-9a-f]{32}$")
EXTENSION_ORIGINAL = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "BMP": ".bmp"}
META = "meta.json"


class RepositorioTrabajos:
    """Guarda, busca, lista y borra trabajos. Los metadatos están en disco, así que sobreviven a un reinicio."""

    def __init__(self, raiz: Path = STORAGE_DIR) -> None:
        self.raiz = raiz

    def _carpeta(self, id: str) -> Path:
        """Carpeta del trabajo. Un id con formato inválido nunca llega a armar una ruta."""
        if not ID_VALIDO.match(id):
            raise TrabajoNoEncontrado(id)
        return self.raiz / id

    def guardar(self, subida: Upload, resultado: ResultadoEdicion, opciones: OpcionesEdicion) -> TrabajoOut:
        """Guarda el original, el resultado y los metadatos de un trabajo nuevo."""
        id = uuid.uuid4().hex
        carpeta = self.raiz / id
        carpeta.mkdir(parents=True)
        original = f"original{EXTENSION_ORIGINAL[subida.photo.format]}"
        final = f"resultado{resultado.extension}"
        (carpeta / original).write_bytes(subida.content)
        (carpeta / final).write_bytes(resultado.contenido)

        trabajo = TrabajoOut(
            id=id, nombre_original=subida.name,
            url=f"{MEDIA_URL}/{id}/{final}", url_original=f"{MEDIA_URL}/{id}/{original}",
            plataforma=opciones.plataforma, formato=resultado.formato,
            ancho=resultado.ancho, alto=resultado.alto, peso_bytes=resultado.peso_bytes,
            calidad=resultado.calidad, avisos=resultado.avisos, opciones=asdict(opciones),
            creado=datetime.now(timezone.utc),
        )
        (carpeta / META).write_text(trabajo.model_dump_json(), encoding="utf-8")
        return trabajo

    def obtener(self, id: str) -> TrabajoOut:
        """Devuelve el trabajo o lanza TrabajoNoEncontrado."""
        meta = self._carpeta(id) / META
        if not meta.is_file():
            raise TrabajoNoEncontrado(id)
        return TrabajoOut.model_validate_json(meta.read_text(encoding="utf-8"))

    def listar(self) -> list[TrabajoOut]:
        """Todos los trabajos, el más nuevo primero."""
        trabajos = [TrabajoOut.model_validate_json(meta.read_text(encoding="utf-8"))
                    for meta in self.raiz.glob(f"*/{META}")]
        return sorted(trabajos, key=lambda t: t.creado, reverse=True)

    def borrar(self, id: str) -> None:
        """Borra todos los archivos del trabajo o lanza TrabajoNoEncontrado."""
        self.obtener(id)  # valida el id y que exista
        shutil.rmtree(self._carpeta(id))
