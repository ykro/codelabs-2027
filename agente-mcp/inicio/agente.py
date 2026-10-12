"""Agente de Taller Volcán: Gemini decide, el servidor MCP ejecuta, la persona aprueba."""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from google import genai
from mcp import Client

MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
URL_MCP = os.environ.get("URL_MCP", "http://localhost:8080/mcp")
MAX_LLAMADAS = 6  # tope de llamadas a Gemini por mensaje: cuida tu cuota gratis
GUATEMALA = timezone(timedelta(hours=-6))
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def instrucciones() -> str:
    hoy = datetime.now(GUATEMALA).date()
    return (
        "Eres el asistente de citas de Taller Volcán, un taller mecánico en Guatemala. "
        "Responde en español, breve y en texto plano (sin Markdown). "
        f"Hoy es {DIAS[hoy.weekday()]} {hoy.isoformat()}. "
        "Usa las herramientas para consultar servicios y horarios; no inventes datos. "
        "Si la persona dice 'en la mañana' o 'en la tarde', elige la primera hora libre de ese rango sin preguntar. "
        "Al pedir una cita, comparte el enlace de aprobación completo y aclara que la cita sigue pendiente "
        "hasta que la persona la apruebe. Tú no puedes aprobar ni confirmar citas."
    )


# TODO paso 7: herramientas_para_gemini(herramientas) traduce las herramientas MCP a funciones de Gemini.


def texto_de(resultado) -> str:
    """El resultado de una herramienta MCP (o su error), como texto para Gemini."""
    return "\n".join(c.text for c in resultado.content if c.type == "text")


# TODO paso 7: turno(...) es el ciclo del agente: Gemini pide herramientas, el cliente MCP las ejecuta.


async def main() -> None:
    gemini = genai.Client()  # usa GEMINI_API_KEY
    async with Client(URL_MCP) as mcp:
        herramientas = (await mcp.list_tools()).tools
        print(f"Conectado a {URL_MCP}: {', '.join(h.name for h in herramientas)}")
        print(f"Modelo: {MODELO}. Escribe 'salir' para terminar.")
        anterior, total = None, 0
        while True:
            try:
                mensaje = (await asyncio.to_thread(input, "\nTú: ")).strip()
            except EOFError:
                break
            if mensaje.lower() in {"salir", "exit", ""}:
                break
            respuesta, anterior, llamadas = await turno(gemini, mcp, herramientas, mensaje, anterior)
            total += llamadas
            print(f"\nAgente: {respuesta}")
            print(f"  (llamadas a Gemini: {llamadas} en este mensaje, {total} en total)")


if __name__ == "__main__":
    asyncio.run(main())
