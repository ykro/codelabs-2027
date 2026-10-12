"""Referencia en línea: la tienda terminada (solucion/) más una página de auditoría pública.

En Cloud Run se copian juntos solucion/ y este archivo (ver desplegar.sh). Agrega:
- /auditoria: audita esta tienda, la tienda de inicio o cualquier URL pública
  (con la protección SSRF del auditor y un límite por visitante).
- /demo/compra: crea una compra de ejemplo por la API UCP, como lo haría un agente,
  y lleva a la página de aprobación.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

import jinja2
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import ucp
from app import AQUI, app, base_de
from auditar import UnsafeURL, audit_store
from catalogo import TIENDA, quetzales

URL_INICIO = os.environ.get("URL_INICIO", "")
POR_VISITANTE = int(os.environ.get("AUDITORIAS_POR_VISITANTE", "8"))  # cada 10 minutos
TOPE_DIARIO = int(os.environ.get("AUDITORIAS_POR_DIA", "400"))
MAX_SESIONES = 500

plantillas = Jinja2Templates(env=jinja2.Environment(loader=jinja2.FileSystemLoader(
    [AQUI / "plantillas_referencia", AQUI / "plantillas"]), autoescape=True))
plantillas.env.globals.update(TIENDA=TIENDA, quetzales=quetzales)

_visitas: dict[str, deque] = defaultdict(deque)
_dia = {"fecha": "", "total": 0}


def visitante(request: Request) -> str:
    reenviado = request.headers.get("x-forwarded-for", "")
    return reenviado.split(",")[0].strip() or (request.client.host if request.client else "?")


def permitido(request: Request) -> str | None:
    hoy = time.strftime("%Y-%m-%d")
    if _dia["fecha"] != hoy:
        _dia.update(fecha=hoy, total=0)
    if _dia["total"] >= TOPE_DIARIO:
        return "Se alcanzó el tope diario de auditorías de esta página. Vuelve mañana."
    marcas = _visitas[visitante(request)]
    while marcas and time.time() - marcas[0] > 600:
        marcas.popleft()
    if len(marcas) >= POR_VISITANTE:
        return f"Hiciste {POR_VISITANTE} auditorías en 10 minutos. Espera un momento."
    marcas.append(time.time())
    _dia["total"] += 1
    return None


@app.get("/auditoria", response_class=HTMLResponse)
async def auditoria(request: Request, url: str = ""):
    propia = base_de(request)
    contexto = {"propia": propia, "inicio": URL_INICIO, "url": url, "reporte": None, "error": None}
    if url:
        contexto["error"] = permitido(request)
        if not contexto["error"]:
            try:
                contexto["reporte"] = await audit_store(url, guard=True)
            except UnsafeURL as e:
                contexto["error"] = str(e)
    return plantillas.TemplateResponse(request, "auditoria.html", contexto)


@app.post("/demo/compra")
async def demo_compra(request: Request):
    """Lo mismo que hace el agente en el paso 4: POST /checkout-sessions. Sin Gemini."""
    if error := permitido(request):
        return HTMLResponse(error, status_code=429)
    while len(ucp.SESIONES) >= MAX_SESIONES:
        ucp.SESIONES.pop(next(iter(ucp.SESIONES)))
    id_sesion = f"chk_{os.urandom(8).hex()}"
    pedido = [{"item": {"id": "hue-250-grueso"}, "quantity": 1}]
    checkout, _ = ucp.armar_checkout(id_sesion, pedido, "estandar", base_de(request))
    ucp.SESIONES[id_sesion] = ucp.firmar(checkout)
    return RedirectResponse(f"/aprobar/{id_sesion}", status_code=303)
