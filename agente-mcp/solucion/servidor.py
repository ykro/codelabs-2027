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


mcp = MCPServer(
    "Taller Volcán",
    instructions=(
        "Agenda de Taller Volcán, taller mecánico en Guatemala. Consulta servicios y horarios cuando quieras. "
        "solicitar_cita solo crea una solicitud PENDIENTE: la persona la aprueba en el enlace que devuelve. "
        "Ninguna herramienta puede aprobar una cita."
    ),
)

CONSULTA = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


@mcp.tool(annotations=CONSULTA)
def ver_servicios() -> dict:
    """Lista los servicios del taller con su id, precio en quetzales y duración en minutos."""
    return {"servicios": [{"id": id_, **datos} for id_, datos in agenda.SERVICIOS.items()]}


@mcp.tool(annotations=CONSULTA)
def ver_horarios(fecha: str) -> dict:
    """Horas libres de un día. fecha en formato AAAA-MM-DD. El taller cierra los domingos."""
    libres = agenda.horas_libres(fecha)
    return {"fecha": fecha, "dia": agenda.fecha_legible(fecha), "horas_libres": libres}


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                      idempotent_hint=False, open_world_hint=False))
def solicitar_cita(servicio_id: str, fecha: str, hora: str, nota: str = "") -> dict:
    """Pide una cita. NO la confirma: crea una solicitud PENDIENTE y devuelve el enlace para que la persona decida."""
    cita = agenda.crear_cita(servicio_id, fecha, hora, nota)
    return agenda.detalle(cita) | {
        "enlace_aprobacion": f"{url_publica()}/aprobar/{cita.id}",
        "importante": "La cita NO está confirmada. Solo la persona puede aprobarla en el enlace.",
    }


@mcp.tool(annotations=CONSULTA)
def estado_cita(cita_id: str) -> dict:
    """Estado de una cita: PENDIENTE, CONFIRMADA o RECHAZADA."""
    if cita_id not in agenda.CITAS:
        raise ToolError(f"No existe la cita {cita_id}.")
    return agenda.detalle(agenda.CITAS[cita_id])


# Páginas para personas: el agente no las usa. Aprobar NO es una herramienta MCP.
@mcp.custom_route("/aprobar/{cita_id}", methods=["GET", "POST"])
async def aprobar(request: Request) -> HTMLResponse:
    cita_id = request.path_params["cita_id"]
    if cita_id not in agenda.CITAS:
        return HTMLResponse(paginas.no_existe(cita_id), status_code=404)
    if request.method == "POST":
        formulario = await request.form()
        agenda.decidir(cita_id, aprobar=formulario.get("decision") == "aprobar")
    return HTMLResponse(paginas.aprobacion(agenda.detalle(agenda.CITAS[cita_id])))


@mcp.custom_route("/citas", methods=["GET"])
async def citas(request: Request) -> HTMLResponse:
    return HTMLResponse(paginas.agenda([agenda.detalle(c) for c in agenda.CITAS.values()]))


@mcp.custom_route("/", methods=["GET"])
async def inicio(request: Request) -> RedirectResponse:
    return RedirectResponse("/citas")


if __name__ == "__main__":
    print(f"Taller Volcán: MCP en http://localhost:{PUERTO}/mcp · aprobaciones en {url_publica()}/aprobar/…")
    mcp.run("streamable-http", host="0.0.0.0", port=PUERTO)
