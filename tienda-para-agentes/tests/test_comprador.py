"""El comprador de punta a punta, con Gemini reemplazado por una elección fija."""

from __future__ import annotations

import contextlib
import io
import re
import sys
import threading
import time

import httpx

import comprador
from conftest import SOLUCION


def test_compra_con_aprobacion(servidor, monkeypatch):
    url = servidor(SOLUCION)
    monkeypatch.setattr(comprador, "elegir", lambda encargo, variantes, hoy: comprador.Eleccion(
        sku="hue-250-grueso", cantidad=1, total_menor_que_q=120, entregar_a_mas_tardar="2099-12-31", razon="prueba"))
    monkeypatch.setattr(sys, "argv", ["comprador.py", url])
    salida = io.StringIO()

    def correr():
        with contextlib.redirect_stdout(salida):
            comprador.main()

    hilo = threading.Thread(target=correr)
    hilo.start()
    for _ in range(100):
        m = re.search(r"/aprobar/(chk_[0-9a-f]+)", salida.getvalue())
        if m:
            break
        time.sleep(0.1)
    assert m, salida.getvalue()
    httpx.post(f"{url}/aprobar/{m.group(1)}", data={"decision": "aprobar"})
    hilo.join(timeout=15)
    texto = salida.getvalue()
    assert "Firma de la tienda verificada" in texto
    assert "Me quedo con Envío estándar." in texto
    assert "✓ Aprobaste la compra" in texto


def test_elige_la_entrega_mas_barata_que_llega_a_tiempo():
    checkout = {
        "totals": [{"type": "total", "amount": 9800}],
        "fulfillment": {"methods": [{"groups": [{"selected_option_id": "estandar", "options": [
            {"id": "estandar", "title": "Envío estándar", "latest_fulfillment_time": "2026-10-20T18:00:00-06:00",
             "totals": [{"type": "total", "amount": 2000}]},
            {"id": "expres", "title": "Exprés en moto", "latest_fulfillment_time": "2026-10-16T18:00:00-06:00",
             "totals": [{"type": "total", "amount": 3500}]},
        ]}]}]},
    }
    eleccion = comprador.Eleccion(sku="x", cantidad=1, total_menor_que_q=120, entregar_a_mas_tardar="2026-10-18", razon="")
    opcion, _ = comprador.mejor_opcion(checkout, eleccion)
    assert opcion["id"] == "expres"
    barata = eleccion.model_copy(update={"total_menor_que_q": 110})
    assert comprador.mejor_opcion(checkout, barata)[0] is None


def test_cuota_agotada_sugiere_otro_modelo(servidor, monkeypatch, capsys):
    import pytest
    from google.genai import errors

    url = servidor(SOLUCION)

    def sin_cuota(*_):
        raise errors.ClientError(429, {"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}})

    monkeypatch.setattr(comprador, "elegir", sin_cuota)
    monkeypatch.setattr(sys, "argv", ["comprador.py", url])
    with pytest.raises(SystemExit):
        comprador.main()
    assert "GEMINI_MODEL=gemini-3.5-flash-lite" in capsys.readouterr().out
