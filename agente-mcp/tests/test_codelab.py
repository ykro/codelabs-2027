"""El codelab y el código concuerdan: cada bloque marcado con archivo aparece textual en solucion/."""

import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
CODELAB = (AQUI / "codelab.md").read_text(encoding="utf-8")
BLOQUES = re.findall(r"^```(\w+) ([\w./-]+)\n(.*?)^```", CODELAB, flags=re.M | re.S)


def test_hay_bloques_de_archivo():
    assert len(BLOQUES) == 5  # servidor.py: 3 (pasos 4 y 6) · agente.py: 2 (paso 7)


def test_bloques_textuales_en_solucion():
    for lenguaje, archivo, codigo in BLOQUES:
        contenido = (AQUI / "solucion" / archivo).read_text(encoding="utf-8")
        assert codigo.strip("\n") in contenido, f"El bloque de {archivo} no aparece textual en solucion/{archivo}"


def test_inicio_es_solucion_menos_los_bloques():
    """Pegar cada bloque en lugar de su TODO convierte inicio/ en solucion/."""
    for archivo in ("servidor.py", "agente.py"):
        inicio = (AQUI / "inicio" / archivo).read_text(encoding="utf-8")
        todos = re.findall(r"^# TODO paso \d+:.*$", inicio, flags=re.M)
        bloques = [c.strip("\n") for _, a, c in BLOQUES if a == archivo]
        assert len(todos) == len(bloques), f"{archivo}: {len(todos)} TODO y {len(bloques)} bloques"
        for todo, bloque in zip(todos, bloques):
            inicio = inicio.replace(todo, bloque, 1)
        assert inicio == (AQUI / "solucion" / archivo).read_text(encoding="utf-8")
    for archivo in ("agenda.py", "paginas.py", "pyproject.toml", "uv.lock"):
        assert (AQUI / "inicio" / archivo).read_bytes() == (AQUI / "solucion" / archivo).read_bytes()


def test_bloques_con_lenguaje():
    aperturas = re.findall(r"^```(\S*)", CODELAB, flags=re.M)
    assert all(a for a in aperturas[::2]), "cada bloque declara su lenguaje"
