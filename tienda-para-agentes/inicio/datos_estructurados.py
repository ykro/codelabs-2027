"""JSON-LD de schema.org para cada página de producto."""

from __future__ import annotations

from typing import Any

from catalogo import ENVIOS, TIENDA, titulo_variante


# TODO paso 5 (jsonld_producto): reemplaza esta función por el JSON-LD del producto.
def jsonld_producto(p: dict, base: str) -> dict[str, Any] | None:
    return None


# TODO paso 5 (detalles_envio): reemplaza esta función por los detalles de envío.
def detalles_envio() -> dict[str, Any] | None:
    return None
