"""Las pruebas corren sobre solucion/ (y arrancan inicio/ en otro proceso para auditarla).

    cd tienda-para-agentes/solucion && uv run pytest ../tests -q
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

TALLER = Path(__file__).resolve().parent.parent
SOLUCION = TALLER / "solucion"
INICIO = TALLER / "inicio"

# La llave de la tienda de las pruebas vive en un directorio temporal, nunca en solucion/.
os.environ.setdefault("LLAVE_TIENDA", str(Path(tempfile.mkdtemp()) / "llave.pem"))
os.environ.pop("URL_PUBLICA", None)
sys.path.insert(0, str(SOLUCION))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def servidor():
    """Arranca una carpeta de la tienda con uvicorn y devuelve su URL."""
    procesos = []

    def arrancar(carpeta: Path) -> str:
        puerto = puerto_libre()
        env = {**os.environ, "LLAVE_TIENDA": str(Path(tempfile.mkdtemp()) / "llave.pem")}
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(puerto)], cwd=carpeta,
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procesos.append(p)
        url = f"http://127.0.0.1:{puerto}"
        for _ in range(100):
            try:
                httpx.get(url + "/api/productos", timeout=1)
                return url
            except httpx.HTTPError:
                time.sleep(0.1)
        raise RuntimeError(f"No arrancó {carpeta}")

    yield arrancar
    for p in procesos:
        p.terminate()


@pytest.fixture()
def cliente():
    from fastapi.testclient import TestClient

    import app as tienda

    return TestClient(tienda.app, headers={"UCP-Agent": 'profile="https://plataforma.example/perfil.json"'})
