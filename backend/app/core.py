"""Instancias únicas del core que comparten los routers."""

from fotoproducto import CatalogoPlataformas, EditorFotoProducto

catalogo = CatalogoPlataformas()
editor = EditorFotoProducto(catalogo)
