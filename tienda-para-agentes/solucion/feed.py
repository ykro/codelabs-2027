"""Feed de productos (RSS 2.0 con el espacio de nombres g: de Merchant Center) y sitemap."""

from __future__ import annotations

from xml.sax.saxutils import escape

from catalogo import ENVIOS, PRODUCTOS, TIENDA, titulo_variante


def feed_xml(base: str) -> str:
    envio = ENVIOS["estandar"]
    items = []
    for p in PRODUCTOS:
        for v in p["variantes"]:
            items.append(f"""  <item>
    <g:id>{v['sku']}</g:id>
    <g:item_group_id>{p['slug']}</g:item_group_id>
    <g:title>{escape(titulo_variante(p, v))}</g:title>
    <g:description>{escape(p['notas'])}</g:description>
    <g:link>{base}/cafe/{p['slug']}?variante={v['sku']}</g:link>
    <g:image_link>{base}/static/img/{p['slug']}.jpg</g:image_link>
    <g:brand>{escape(TIENDA['nombre'])}</g:brand>
    <g:condition>new</g:condition>
    <g:price>{v['precio'] / 100:.2f} GTQ</g:price>
    <g:availability>{'in_stock' if v['disponible'] else 'out_of_stock'}</g:availability>
    <g:size>{escape(v['presentacion'])}</g:size>
    <g:min_handling_time>{envio['preparacion'][0]}</g:min_handling_time>
    <g:max_handling_time>{envio['preparacion'][1]}</g:max_handling_time>
    <g:shipping>
      <g:country>GT</g:country>
      <g:service>{envio['titulo']}</g:service>
      <g:price>{envio['precio'] / 100:.2f} GTQ</g:price>
      <g:min_transit_time>{envio['transito'][0]}</g:min_transit_time>
      <g:max_transit_time>{envio['transito'][1]}</g:max_transit_time>
    </g:shipping>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
<channel>
  <title>{escape(TIENDA['nombre'])}</title>
  <link>{base}/</link>
  <description>{escape(TIENDA['lema'])}</description>
{chr(10).join(items)}
</channel>
</rss>
"""


def sitemap_xml(base: str) -> str:
    urls = [f"{base}/cafe/{p['slug']}" for p in PRODUCTOS] + [f"{base}/", f"{base}/envios"]
    entradas = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entradas}
</urlset>
"""
