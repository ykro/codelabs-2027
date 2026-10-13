"""Referencia en línea: el mismo servidor MCP y el mismo agente del codelab, con una página de chat.

Diferencias con lo que construye el alumno:
- Gemini corre en el servidor vía Vertex AI con las credenciales del servicio (sin llaves en el código).
- El agente se conecta al servidor MCP en memoria (mismo proceso), no por HTTP.
- Límite de mensajes por visitante y tope diario. Los datos se borran cada día.
"""

import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from google import genai
from mcp import Client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route

import agenda
import agente
import paginas
import servidor

LIMITE_VISITANTE = int(os.environ.get("LIMITE_VISITANTE", "15"))  # mensajes por visitante al día
TOPE_DIARIO = int(os.environ.get("TOPE_DIARIO", "200"))  # mensajes de todos al día
MAX_CITAS = 300
CHAT = (Path(__file__).parent / "chat.html").read_text(encoding="utf-8")

gemini = genai.Client()  # GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT y GOOGLE_CLOUD_LOCATION
estado = {"dia": agenda.hoy(), "total": 0, "por_visitante": {}, "propias": {}}
COOKIE = "tv_visitante"
ENLACE = re.compile(r"/aprobar/(TV-[0-9A-F]+)")


def nuevo_dia() -> None:
    if estado["dia"] != agenda.hoy():
        agenda.CITAS.clear()
        estado.update(dia=agenda.hoy(), total=0, por_visitante={}, propias={})


def visitante(request: Request) -> str:
    """IP del visitante. Cloud Run agrega la IP real al FINAL de X-Forwarded-For; lo anterior lo escribe el cliente."""
    reenviado = request.headers.get("x-forwarded-for", "")
    return reenviado.split(",")[-1].strip() or (request.client.host if request.client else "?")


def citas_propias(token: str | None) -> set[str]:
    return estado["propias"].get(token or "", set())


async def pagina_chat(request: Request) -> HTMLResponse:
    html = CHAT.replace("{{LIMITE}}", str(LIMITE_VISITANTE)).replace("{{MODELO}}", agente.MODELO)
    respuesta = HTMLResponse(html)
    if not request.cookies.get(COOKIE):
        respuesta.set_cookie(COOKIE, secrets.token_urlsafe(16), max_age=86400, httponly=True, secure=True, samesite="lax")
    return respuesta


async def api_chat(request: Request) -> JSONResponse:
    nuevo_dia()
    datos = await request.json()
    mensaje = str(datos.get("mensaje", "")).strip()[:400]
    anterior = datos.get("anterior") or None
    if not mensaje:
        return JSONResponse({"error": "Escribe un mensaje."}, status_code=400)
    quien = visitante(request)
    usados = estado["por_visitante"].get(quien, 0)
    if usados >= LIMITE_VISITANTE:
        return JSONResponse({"error": f"Llegaste al límite de {LIMITE_VISITANTE} mensajes por hoy. "
                                      "Haz el codelab y corre tu propio agente."}, status_code=429)
    if estado["total"] >= TOPE_DIARIO or len(agenda.CITAS) >= MAX_CITAS:
        return JSONResponse({"error": "La demo llegó a su tope de hoy. Vuelve mañana."}, status_code=429)
    estado["por_visitante"][quien] = usados + 1
    estado["total"] += 1
    pasos: list[str] = []
    try:
        async with Client(servidor.mcp) as mcp:
            herramientas = (await mcp.list_tools()).tools
            respuesta, anterior, llamadas = await agente.turno(
                gemini, mcp, herramientas, mensaje, anterior, avisar=pasos.append)
    except Exception:  # noqa: BLE001 — al visitante no le mostramos detalles internos
        return JSONResponse({"error": "El agente no pudo responder. Intenta de nuevo."}, status_code=502)
    token = request.cookies.get(COOKIE)
    if token:  # quien recibe el enlace de aprobación es dueño de esa cita
        estado["propias"].setdefault(token, set()).update(ENLACE.findall(respuesta))
    return JSONResponse({"respuesta": respuesta, "anterior": anterior, "pasos": pasos, "llamadas": llamadas,
                         "restantes": LIMITE_VISITANTE - usados - 1})


app_mcp = servidor.mcp.streamable_http_app(host="0.0.0.0")


async def guardia(scope, receive, send):
    """/mcp es público con tope de citas. /aprobar y /citas solo muestran las citas de quien las pidió."""
    if scope["type"] == "http":
        ruta = scope["path"]
        if ruta.startswith("/mcp"):
            nuevo_dia()
            if len(agenda.CITAS) >= MAX_CITAS:
                await JSONResponse({"error": "tope de hoy"}, status_code=503)(scope, receive, send)
                return
        elif ruta.startswith("/aprobar/") or ruta == "/citas":
            token = Request(scope).cookies.get(COOKIE)
            propias = citas_propias(token)
            if ruta == "/citas":
                lista = [agenda.detalle(c) for i, c in agenda.CITAS.items() if i in propias]
                await HTMLResponse(paginas.agenda(lista))(scope, receive, send)
                return
            if ruta.removeprefix("/aprobar/") not in propias:
                await HTMLResponse(paginas.no_existe(ruta.removeprefix("/aprobar/")), status_code=404)(scope, receive, send)
                return
    await app_mcp(scope, receive, send)


@asynccontextmanager
async def ciclo(app):
    async with servidor.mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/", pagina_chat),
        Route("/api/chat", api_chat, methods=["POST"]),
        Route("/salud", lambda r: JSONResponse({"ok": True})),
        Mount("/", app=guardia),  # /aprobar/<id>, /citas y /mcp del servidor del codelab
    ],
    lifespan=ciclo,
)
