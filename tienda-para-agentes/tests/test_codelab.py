"""El codelab y el código coinciden: cada bloque que el alumno pega está textual en
solucion/, y aplicar todos los bloques sobre inicio/ da exactamente solucion/."""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path

from aplicar_codelab import aplicar, bloques
from conftest import INICIO, SOLUCION, TALLER

CODELAB = (TALLER / "codelab.md").read_text(encoding="utf-8")
IGNORAR = {".venv", "__pycache__", ".pytest_cache", ".llave_tienda.pem"}


def test_cada_bloque_esta_en_solucion():
    encontrados = bloques(CODELAB)
    assert len(encontrados) >= 10
    for b in encontrados:
        texto = (SOLUCION / b["archivo"]).read_text(encoding="utf-8")
        assert b["codigo"] in texto, f"El bloque del paso {b['paso']} no está en solucion/{b['archivo']}"


def test_inicio_mas_bloques_es_solucion(tmp_path: Path):
    copia = tmp_path / "inicio"
    shutil.copytree(INICIO, copia, ignore=shutil.ignore_patterns(*IGNORAR))
    for b in bloques(CODELAB):
        if b["todo"]:
            aplicar(b, copia)

    def comparar(a: Path, b: Path):
        cmp = filecmp.dircmp(a, b, ignore=list(IGNORAR))
        assert not cmp.left_only and not cmp.right_only, (cmp.left_only, cmp.right_only)
        for nombre in cmp.common_files:
            assert (a / nombre).read_bytes() == (b / nombre).read_bytes(), f"{a / nombre} difiere"
        for sub in cmp.common_dirs:
            comparar(a / sub, b / sub)

    comparar(copia, SOLUCION)


def test_no_quedan_todo_en_solucion():
    for ruta in SOLUCION.rglob("*"):
        if ruta.is_file() and ruta.suffix in {".py", ".html"} and ".venv" not in ruta.parts:
            assert "TODO paso" not in ruta.read_text(encoding="utf-8"), ruta


def test_cada_todo_de_inicio_tiene_su_bloque():
    ids = {b["todo"] for b in bloques(CODELAB)}
    import re

    for ruta in INICIO.rglob("*"):
        if ruta.is_file() and ruta.suffix in {".py", ".html"} and ".venv" not in ruta.parts:
            for todo in re.findall(r"TODO paso \d+ \((\w+)\)", ruta.read_text(encoding="utf-8")):
                assert todo in ids, f"{ruta.name}: TODO ({todo}) sin bloque en el codelab"


def test_bloques_declaran_lenguaje():
    import re

    aperturas = re.findall(r"^```([^\n]*)\n(?:.*?)^```[ \t]*$", CODELAB, re.M | re.S)
    assert aperturas and all(a.split(" ")[0] for a in aperturas), "Hay un bloque de código sin lenguaje"
