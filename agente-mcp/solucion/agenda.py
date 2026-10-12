"""Agenda de Taller Volcán: servicios, horarios y citas.

Datos ficticios, en memoria. Si reinicias el servidor, la agenda vuelve a empezar.
Este archivo ya viene completo: el taller se trata de exponerlo a un agente.
"""

from __future__ import annotations

import random
import secrets
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone

from mcp.server.mcpserver.exceptions import ToolError  # su mensaje sí le llega al agente

GUATEMALA = timezone(timedelta(hours=-6))  # Guatemala no usa horario de verano
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

SERVICIOS = {
    "cambio-aceite": {"nombre": "Cambio de aceite y filtro", "precio_q": 350, "duracion_min": 45},
    "frenos": {"nombre": "Revisión de frenos", "precio_q": 200, "duracion_min": 60},
    "alineacion": {"nombre": "Alineación y balanceo", "precio_q": 275, "duracion_min": 60},
    "diagnostico": {"nombre": "Diagnóstico por computadora", "precio_q": 250, "duracion_min": 30},
    "afinamiento": {"nombre": "Afinamiento mayor", "precio_q": 1200, "duracion_min": 180},
}

HORAS_SEMANA = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
HORAS_SABADO = ["08:00", "09:00", "10:00", "11:00"]
DIAS_ABIERTOS = 30  # se puede pedir cita hasta 30 días adelante


@dataclass
class Cita:
    id: str
    servicio_id: str
    fecha: str  # AAAA-MM-DD
    hora: str  # HH:MM
    estado: str = "PENDIENTE"  # PENDIENTE → CONFIRMADA o RECHAZADA (solo la persona decide)
    nota: str = ""


CITAS: dict[str, Cita] = {}


def hoy() -> date:
    return datetime.now(GUATEMALA).date()


def fecha_legible(fecha: str) -> str:
    d = date.fromisoformat(fecha)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def leer_fecha(fecha: str) -> date:
    try:
        d = date.fromisoformat(fecha)
    except ValueError:
        raise ToolError(f"Fecha inválida: {fecha!r}. Usa el formato AAAA-MM-DD, por ejemplo 2026-10-16.")
    if d < hoy() or d > hoy() + timedelta(days=DIAS_ABIERTOS):
        raise ToolError(f"Solo hay agenda de hoy ({hoy()}) a {DIAS_ABIERTOS} días.")
    return d


def horas_libres(fecha: str) -> list[str]:
    d = leer_fecha(fecha)
    if d.weekday() == 6:
        return []  # domingo cerrado
    horas = HORAS_SABADO if d.weekday() == 5 else HORAS_SEMANA
    ocupadas = set(random.Random(fecha).sample(horas, 2))  # otros clientes (siempre las mismas por fecha)
    ocupadas |= {c.hora for c in CITAS.values() if c.fecha == fecha and c.estado != "RECHAZADA"}
    if d == hoy():
        ahora = datetime.now(GUATEMALA).strftime("%H:%M")
        ocupadas |= {h for h in horas if h <= ahora}
    return [h for h in horas if h not in ocupadas]


def crear_cita(servicio_id: str, fecha: str, hora: str, nota: str = "") -> Cita:
    if servicio_id not in SERVICIOS:
        raise ToolError(f"No existe el servicio {servicio_id!r}. Usa un id de ver_servicios.")
    if hora not in horas_libres(fecha):
        raise ToolError(f"La hora {hora} del {fecha} no está libre. Consulta ver_horarios.")
    cita = Cita(id=f"TV-{secrets.token_hex(3).upper()}", servicio_id=servicio_id, fecha=fecha, hora=hora, nota=nota[:200])
    CITAS[cita.id] = cita
    return cita


def decidir(cita_id: str, aprobar: bool) -> Cita:
    """Solo la llama la página de aprobación, nunca una herramienta MCP."""
    cita = CITAS[cita_id]
    if cita.estado == "PENDIENTE":
        cita.estado = "CONFIRMADA" if aprobar else "RECHAZADA"
    return cita


def detalle(cita: Cita) -> dict:
    servicio = SERVICIOS[cita.servicio_id]
    return asdict(cita) | {
        "servicio": servicio["nombre"],
        "precio_q": servicio["precio_q"],
        "dia": fecha_legible(cita.fecha),
    }
