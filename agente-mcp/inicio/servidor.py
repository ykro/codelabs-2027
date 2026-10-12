"""Servidor MCP de Taller Volcán: herramientas para agentes + página de aprobación para personas."""

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

import agenda
import paginas

PUERTO = int(os.environ.get("PORT", "8080"))


def url_publica() -> str:
    """La dirección con la que la persona abre la página de aprobación."""
    if os.environ.get("URL_PUBLICA"):
        return os.environ["URL_PUBLICA"].rstrip("/")
    if os.environ.get("WEB_HOST"):  # Cloud Shell: la vista previa web vive en https://PUERTO-$WEB_HOST
        return f"https://{PUERTO}-{os.environ['WEB_HOST']}"
    return f"http://localhost:{PUERTO}"


# TODO paso 4: crea el servidor MCP y las herramientas de consulta (ver_servicios, ver_horarios).


# TODO paso 6: agrega solicitar_cita y estado_cita.


# TODO paso 6: agrega la página de aprobación /aprobar/{cita_id}.


@mcp.custom_route("/citas", methods=["GET"])
async def citas(request: Request) -> HTMLResponse:
    return HTMLResponse(paginas.agenda([agenda.detalle(c) for c in agenda.CITAS.values()]))


@mcp.custom_route("/", methods=["GET"])
async def inicio(request: Request) -> RedirectResponse:
    return RedirectResponse("/citas")


if __name__ == "__main__":
    print(f"Taller Volcán: MCP en http://localhost:{PUERTO}/mcp · aprobaciones en {url_publica()}/aprobar/…")
    mcp.run("streamable-http", host="0.0.0.0", port=PUERTO)
