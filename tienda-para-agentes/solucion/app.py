"""Tostaduría Barrilete: la tienda en línea (FastAPI).

    uv run uvicorn app:app --port 8080 --reload
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ucp
from catalogo import ENVIOS, PRODUCTOS, TIENDA, producto, quetzales, rango_fechas, variante, ventana_entrega
from datos_estructurados import jsonld_producto
from feed import feed_xml, sitemap_xml

AQUI = Path(__file__).parent
app = FastAPI(title=TIENDA["nombre"], docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
plantillas = Jinja2Templates(directory=AQUI / "plantillas")
plantillas.env.globals.update(TIENDA=TIENDA, quetzales=quetzales)

PEDIDOS_WEB: dict[str, dict] = {}


def base_de(request: Request) -> str:
    return str(request.base_url).rstrip("/")


# --- Páginas que ya funcionan ---------------------------------------------------------

@app.get("/api/productos")
def api_productos():
    """Los datos que usa la versión de la tienda que se dibuja con JavaScript."""
    return JSONResponse(PRODUCTOS)


@app.get("/envios", response_class=HTMLResponse)
def envios(request: Request):
    return plantillas.TemplateResponse(request, "envios.html", {
        "envios": ENVIOS, "estandar": rango_fechas(*ventana_entrega("estandar")),
        "expres": rango_fechas(*ventana_entrega("expres"))})


@app.get("/terminos", response_class=HTMLResponse)
def terminos(request: Request):
    return plantillas.TemplateResponse(request, "terminos.html", {})


@app.post("/pedidos", response_class=HTMLResponse)
def pedir(request: Request, sku: str = Form(...), cantidad: int = Form(1), nombre: str = Form("")):
    """El pedido de una persona desde la ficha del producto (pago contra entrega)."""
    p, v = variante(sku)
    if v is None or not v["disponible"] or not 1 <= cantidad <= 10:
        return HTMLResponse("Esa presentación no está disponible.", status_code=400)
    id_pedido = f"web_{secrets.token_hex(4)}"
    PEDIDOS_WEB[id_pedido] = {"id": id_pedido, "p": p, "v": v, "cantidad": cantidad, "nombre": nombre[:80]}
    return plantillas.TemplateResponse(request, "pedido_web.html", {"pedido": PEDIDOS_WEB[id_pedido]})


@app.get("/pedidos/{id_pedido}", response_class=HTMLResponse)
def ver_pedido(id_pedido: str, request: Request):
    pedido = ucp.PEDIDOS.get(id_pedido)
    if pedido is None:
        return HTMLResponse("Pedido no encontrado", status_code=404)
    return plantillas.TemplateResponse(request, "pedido.html", {"c": pedido["checkout"]})


# --- Paso 4: portada y fichas de producto ---------------------------------------------

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return plantillas.TemplateResponse(request, "inicio.html", {"productos": PRODUCTOS})


@app.get("/cafe/{slug}", response_class=HTMLResponse)
def ver_producto(slug: str, request: Request):
    p = producto(slug)
    if p is None:
        return HTMLResponse("Producto no encontrado", status_code=404)
    jsonld = jsonld_producto(p, base_de(request))
    return plantillas.TemplateResponse(request, "producto.html", {"p": p, "jsonld": jsonld})


# --- Paso 6: feed de productos y sitemap ----------------------------------------------

@app.get("/feed.xml")
def feed(request: Request):
    return Response(feed_xml(base_de(request)), media_type="application/xml")


@app.get("/sitemap.xml")
def sitemap(request: Request):
    return Response(sitemap_xml(base_de(request)), media_type="application/xml")


# --- Paso 7: perfil de comercio UCP ---------------------------------------------------

@app.get("/.well-known/ucp")
def perfil_ucp(request: Request):
    return JSONResponse(ucp.perfil(base_de(request)), headers={"cache-control": "public, max-age=60"})


# --- Paso 7: sesiones de checkout -----------------------------------------------------

app.include_router(ucp.rutas)


# --- Paso 9: la persona aprueba -------------------------------------------------------

@app.get("/aprobar/{id_sesion}", response_class=HTMLResponse)
def ver_aprobacion(id_sesion: str, request: Request):
    sesion = ucp.SESIONES.get(id_sesion)
    if sesion is None:
        return HTMLResponse("Esta solicitud de compra no existe o ya expiró.", status_code=404)
    return plantillas.TemplateResponse(request, "aprobar.html", {"c": sesion})


@app.post("/aprobar/{id_sesion}")
def decidir(id_sesion: str, request: Request, decision: str = Form(...)):
    if decision == "aprobar":
        cerrada = ucp.completar(id_sesion, base_de(request))
    else:
        cerrada = ucp.cancelar(id_sesion)
    if cerrada is None:
        return HTMLResponse("Esta compra ya se cerró o expiró.", status_code=409)
    return RedirectResponse(f"/aprobar/{id_sesion}", status_code=303)
