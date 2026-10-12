"""Pruebas de solucion/: servidor MCP, página de aprobación y ciclo del agente (sin red ni Gemini)."""

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from mcp import Client
from starlette.testclient import TestClient

import agenda
import agente
import servidor


def proximo(dia_semana: int) -> str:
    d = agenda.hoy() + timedelta(days=1)
    while d.weekday() != dia_semana:
        d += timedelta(days=1)
    return d.isoformat()


@pytest.fixture(autouse=True)
def agenda_limpia():
    agenda.CITAS.clear()
    yield
    agenda.CITAS.clear()


async def llamar(nombre, argumentos=None):
    async with Client(servidor.mcp) as c:
        return await c.call_tool(nombre, argumentos or {})


async def test_herramientas_y_anotaciones():
    async with Client(servidor.mcp) as c:
        herramientas = {h.name: h for h in (await c.list_tools()).tools}
    assert set(herramientas) == {"ver_servicios", "ver_horarios", "solicitar_cita", "estado_cita"}
    assert not any("aprob" in n for n in herramientas), "aprobar nunca es una herramienta"
    for n in ("ver_servicios", "ver_horarios", "estado_cita"):
        assert herramientas[n].annotations.read_only_hint is True
        assert herramientas[n].annotations.idempotent_hint is True
    pedir = herramientas["solicitar_cita"].annotations
    assert pedir.read_only_hint is False and pedir.destructive_hint is False and pedir.idempotent_hint is False


async def test_ver_servicios_y_horarios():
    servicios = json.loads((await llamar("ver_servicios")).content[0].text)["servicios"]
    assert {s["id"] for s in servicios} >= {"cambio-aceite", "frenos"}
    domingo = json.loads((await llamar("ver_horarios", {"fecha": proximo(6)})).content[0].text)
    assert domingo["horas_libres"] == []
    viernes = json.loads((await llamar("ver_horarios", {"fecha": proximo(4)})).content[0].text)
    assert len(viernes["horas_libres"]) == 5 and viernes["dia"].startswith("viernes")


async def test_error_legible_para_el_agente():
    r = await llamar("ver_horarios", {"fecha": "viernes"})
    assert r.is_error and "AAAA-MM-DD" in r.content[0].text


async def test_solicitar_no_confirma_y_la_persona_aprueba():
    fecha = proximo(4)
    hora = json.loads((await llamar("ver_horarios", {"fecha": fecha})).content[0].text)["horas_libres"][0]
    cita = json.loads((await llamar("solicitar_cita", {"servicio_id": "cambio-aceite", "fecha": fecha, "hora": hora})).content[0].text)
    assert cita["estado"] == "PENDIENTE"
    assert cita["enlace_aprobacion"].endswith(f"/aprobar/{cita['id']}")
    libres = json.loads((await llamar("ver_horarios", {"fecha": fecha})).content[0].text)["horas_libres"]
    assert hora not in libres, "una solicitud pendiente aparta el horario"
    otra = await llamar("solicitar_cita", {"servicio_id": "cambio-aceite", "fecha": fecha, "hora": hora})
    assert otra.is_error

    web = TestClient(servidor.mcp.streamable_http_app())
    pagina = web.get(f"/aprobar/{cita['id']}")
    assert pagina.status_code == 200 and "Aprobar cita" in pagina.text
    assert web.post(f"/aprobar/{cita['id']}", data={"decision": "aprobar"}).status_code == 200
    estado = json.loads((await llamar("estado_cita", {"cita_id": cita["id"]})).content[0].text)
    assert estado["estado"] == "CONFIRMADA"
    assert web.post(f"/aprobar/{cita['id']}", data={"decision": "rechazar"}).status_code == 200
    assert agenda.CITAS[cita["id"]].estado == "CONFIRMADA", "una decisión no se cambia"
    assert web.get("/aprobar/TV-NOEXISTE").status_code == 404
    assert cita["id"] in web.get("/citas").text


async def test_rechazar_libera_el_horario():
    fecha = proximo(4)
    cita = agenda.crear_cita("frenos", fecha, "16:00")
    TestClient(servidor.mcp.streamable_http_app()).post(f"/aprobar/{cita.id}", data={"decision": "rechazar"})
    assert agenda.CITAS[cita.id].estado == "RECHAZADA"
    assert "16:00" in agenda.horas_libres(fecha)


def test_url_publica(monkeypatch):
    monkeypatch.delenv("URL_PUBLICA", raising=False)
    monkeypatch.setenv("WEB_HOST", "cs-ejemplo.cloudshell.dev")
    assert servidor.url_publica() == "https://8080-cs-ejemplo.cloudshell.dev"
    monkeypatch.setenv("URL_PUBLICA", "https://ejemplo.run.app/")
    assert servidor.url_publica() == "https://ejemplo.run.app"


class GeminiFalso:
    """Imita client.aio.interactions.create: primero pide herramientas, luego responde."""

    def __init__(self, guion):
        self.guion, self.llamadas = list(guion), []
        self.aio = SimpleNamespace(interactions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.llamadas.append(kwargs)
        pasos = self.guion.pop(0)
        texto = next((p["texto"] for p in pasos if "texto" in p), "")
        steps = [SimpleNamespace(type="function_call", id=f"c{i}", name=p["name"], arguments=p["args"])
                 for i, p in enumerate(pasos) if "name" in p]
        return SimpleNamespace(id=f"i{len(self.llamadas)}", steps=steps, output_text=texto)


async def test_ciclo_del_agente():
    fecha = proximo(4)
    gemini = GeminiFalso([
        [{"name": "ver_servicios", "args": {}}, {"name": "ver_horarios", "args": {"fecha": fecha}}],
        [{"name": "solicitar_cita", "args": {"servicio_id": "cambio-aceite", "fecha": fecha, "hora": "08:00"}}],
        [{"texto": "Listo, aprueba en el enlace."}],
    ])
    avisos = []
    async with Client(servidor.mcp) as mcp:
        herramientas = (await mcp.list_tools()).tools
        respuesta, anterior, llamadas = await agente.turno(gemini, mcp, herramientas, "agenda", avisar=avisos.append)
    assert respuesta == "Listo, aprueba en el enlace." and llamadas == 3 and anterior == "i3"
    assert [a.split(":")[0].strip() for a in avisos] == ["· consulta", "· consulta", "· pide (necesita tu aprobación)"]
    segunda = gemini.llamadas[1]
    assert segunda["previous_interaction_id"] == "i1"
    assert [r["name"] for r in segunda["input"]] == ["ver_servicios", "ver_horarios"]
    assert all(f["type"] == "function" for f in segunda["tools"])
    assert len(agenda.CITAS) == 1 and next(iter(agenda.CITAS.values())).estado == "PENDIENTE"


async def test_el_agente_se_detiene():
    gemini = GeminiFalso([[{"name": "ver_servicios", "args": {}}]] * 10)
    async with Client(servidor.mcp) as mcp:
        herramientas = (await mcp.list_tools()).tools
        _, _, llamadas = await agente.turno(gemini, mcp, herramientas, "hola", avisar=lambda _: None)
    assert llamadas == agente.MAX_LLAMADAS
