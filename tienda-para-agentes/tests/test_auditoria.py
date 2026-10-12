"""El auditor: 0/8 para la tienda de inicio/, 8/8 para solucion/, y protección SSRF."""

from __future__ import annotations

import asyncio

import pytest

from auditar import UnsafeURL, audit_store
from conftest import INICIO, SOLUCION


def test_inicio_saca_0_de_8(servidor):
    reporte = asyncio.run(audit_store(servidor(INICIO)))
    assert reporte["score"] == 0, [i["key"] for i in reporte["items"] if i["ok"]]


def test_solucion_saca_8_de_8(servidor):
    reporte = asyncio.run(audit_store(servidor(SOLUCION)))
    assert reporte["score"] == 8, [i for i in reporte["items"] if not i["ok"]]


@pytest.mark.parametrize("url", ["http://127.0.0.1:8080", "http://169.254.169.254/computeMetadata/v1",
                                 "http://10.0.0.1", "file:///etc/passwd", "http://localhost"])
def test_proteccion_ssrf(url):
    with pytest.raises(UnsafeURL):
        asyncio.run(audit_store(url, guard=True))
