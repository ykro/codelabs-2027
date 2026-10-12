"""Feed de productos (RSS 2.0 con el espacio de nombres g: de Merchant Center) y sitemap."""

from __future__ import annotations

from xml.sax.saxutils import escape

from catalogo import ENVIOS, PRODUCTOS, TIENDA, titulo_variante


# TODO paso 6 (feed_xml): reemplaza esta función por el feed de productos.
def feed_xml(base: str) -> str:
    return ""


# TODO paso 6 (sitemap_xml): reemplaza esta función por el mapa del sitio.
def sitemap_xml(base: str) -> str:
    return ""
