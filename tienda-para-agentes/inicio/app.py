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

# TODO paso 4 (paginas_servidor): estas dos rutas mandan un HTML vacío que se dibuja con
# JavaScript. Reemplázalas para que el servidor mande el contenido.
@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return plantillas.TemplateResponse(request, "shell.html", {})


@app.get("/cafe/{slug}", response_class=HTMLResponse)
def ver_producto(slug: str, request: Request):
    return plantillas.TemplateResponse(request, "shell.html", {})


# --- Paso 6: feed de productos y sitemap ----------------------------------------------

# TODO paso 6 (rutas_feed): agrega aquí las rutas /feed.xml y /sitemap.xml.


# --- Paso 7: perfil de comercio UCP ---------------------------------------------------

# TODO paso 7 (ruta_perfil): agrega aquí la ruta /.well-known/ucp.


# --- Paso 7: sesiones de checkout -----------------------------------------------------

# TODO paso 7 (incluir_rutas): conecta aquí las rutas de checkout de ucp.py.


# --- Paso 9: la persona aprueba -------------------------------------------------------

# TODO paso 9 (rutas_aprobar): agrega aquí la página de aprobación.
