"""Pruebas del taller «Entrena a tu propio David».

    uv run --with pytest pytest entrena-tu-david/tests -q

- El dataset cumple el esquema y las reglas de generación; train y test no comparten mensajes.
- Cada bloque de código del codelab marcado como celda (```python celda) aparece textual en el notebook de solución.
- El notebook de inicio es el de solución sin las celdas TODO.
- Las funciones de calificación del notebook se comportan como dice el codelab.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

TALLER = Path(__file__).resolve().parent.parent
DATOS = TALLER / "datos"
SOLUCION = TALLER / "solucion" / "entrena_tu_david.ipynb"
INICIO = TALLER / "inicio" / "entrena_tu_david.ipynb"
CODELAB = TALLER / "codelab.md"

spec = importlib.util.spec_from_file_location("generar_datos", DATOS / "generar_datos.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def filas(nombre):
    return [json.loads(l) for l in (DATOS / nombre).read_text(encoding="utf-8").splitlines() if l.strip()]


def celdas(ruta):
    nb = json.loads(ruta.read_text(encoding="utf-8"))
    return [(c["cell_type"], "".join(c["source"])) for c in nb["cells"]]


# ------------------------------------------------------------------ dataset
@pytest.mark.parametrize("nombre,n", [("train.jsonl", 1000), ("test.jsonl", 150)])
def test_dataset_valido(nombre, n):
    datos = filas(nombre)
    assert len(datos) == n
    for r in datos:
        assert set(r) == {"id", "mensaje", "ticket", "origen"}
        assert gen.validar_ticket(r["ticket"]) == [], r["id"]
        assert r["ticket"]["producto"] in gen.PRODUCTOS
        assert gen.PRODUCTOS[r["ticket"]["producto"]][0] == r["ticket"]["categoria"]
        assert r["origen"]["tipo"] == "sintetico" and r["origen"]["modelo"]
        assert gen.validar(r["mensaje"], r["ticket"], r["origen"]["pistas"]) == [], r["id"]


def test_test_separado_de_train():
    train = {gen.normalizar(r["mensaje"]) for r in filas("train.jsonl")}
    test = {gen.normalizar(r["mensaje"]) for r in filas("test.jsonl")}
    assert not train & test


def test_reglas_rechazan_mensajes_malos():
    t = {"tipo": "pedido", "categoria": "obra_gris", "producto": "cemento", "cantidad": 10, "monto_q": None, "urgencia": "alta"}
    p = {"producto_como": ["cemento"], "cantidad_como": "10", "monto_como": None, "urgencia_como": "para hoy", "estilo": []}
    assert gen.validar("buenas, necesito 10 bolsas de cemento para hoy", t, p) == []
    assert "cantidad" in gen.validar("buenas, necesito 12 bolsas de cemento para hoy", t, p)
    assert any(f.startswith("urgencia_mezclada") for f in gen.validar("necesito 10 de cemento para hoy o para el sabado", t, p))
    assert any(f.startswith("otro_producto") for f in gen.validar("necesito 10 de cemento y una pala para hoy", t, p))
    assert "dinero_sin_monto" in gen.validar("necesito 10 de cemento para hoy, tengo pisto", t, p)
    # coherencia: cotizar en un pedido, o una fuga con cemento, no tienen sentido
    assert any(f.startswith("incoherente") for f in gen.validar("quiero 10 de cemento para hoy, solo estoy cotizando", t, p))
    assert any(f.startswith("incoherente") for f in gen.validar("necesito 10 de cemento para hoy, tengo una fuga", t, p))
    assert "tengo una fuga" not in gen.senales_posibles(t) and "solo estoy cotizando" not in gen.senales_posibles({**t, "urgencia": "baja"})


# ------------------------------------------------------------------ notebook ↔ codelab
def test_bloques_del_codelab_estan_en_la_solucion():
    md = CODELAB.read_text(encoding="utf-8")
    bloques = re.findall(r"^```python celda[^\n]*\n(.*?)^```", md, flags=re.M | re.S)
    assert len(bloques) >= 8
    codigo = [src for tipo, src in celdas(SOLUCION) if tipo == "code"]
    for b in bloques:
        assert b.strip("\n") in codigo, f"No está en solucion/: {b[:80]!r}"


def test_inicio_es_solucion_sin_los_todo():
    sol, ini = celdas(SOLUCION), celdas(INICIO)
    assert len(sol) == len(ini)
    todos = 0
    for (t1, s1), (t2, s2) in zip(sol, ini):
        assert t1 == t2
        if s2.startswith("# TODO"):
            todos += 1
        else:
            assert s1 == s2
    assert todos == 4


def test_solucion_tiene_salidas_de_la_corrida():
    nb = json.loads(SOLUCION.read_text(encoding="utf-8"))
    codigo = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert all(c.get("outputs") is not None for c in codigo)
    for c in codigo:
        src = "".join(c["source"])
        if "\ndef " not in "\n" + src and any(k in src for k in ("print(", "tabla(**", "!nvidia-smi", "!ls", "pd.DataFrame(", "app.launch(")):
            assert c.get("outputs"), f"sin salida: {src[:60]!r}"


# ------------------------------------------------------------------ calificación
@pytest.fixture(scope="module")
def calif():
    ns = {}
    exec("import json\nimport pandas as pd", ns)
    src = next(s for t, s in celdas(SOLUCION) if t == "code" and "def calificar(" in s)
    exec(src, ns)
    return ns


def test_leer_ticket(calif):
    bueno = {"tipo": "pedido", "categoria": "obra_gris", "producto": "cemento", "cantidad": 3, "monto_q": None, "urgencia": "alta"}
    txt = json.dumps(bueno)
    assert calif["leer_ticket"](txt) == bueno
    assert calif["leer_ticket"]("```json\n" + txt + "\n```") == bueno
    assert calif["leer_ticket"]("Claro, aquí está: " + txt) is None
    assert calif["leer_ticket"](json.dumps({**bueno, "categoria": "construccion"})) is None
    assert calif["leer_ticket"](json.dumps({k: v for k, v in bueno.items() if k != "monto_q"})) is None


def test_calificar(calif):
    esperado = {"tipo": "pedido", "categoria": "obra_gris", "producto": "cemento", "cantidad": 3, "monto_q": 250, "urgencia": "alta"}
    fila = [{"ticket": esperado}]
    r = calif["calificar"]([json.dumps(esperado)], fila)
    assert r["JSON válido"] == r["Campos correctos"] == r["Tickets perfectos"] == 1
    casi = {**esperado, "producto": "Cemento gris", "monto_q": 250.0}
    r = calif["calificar"]([json.dumps(casi)], fila)
    assert r["Tickets perfectos"] == 0 and abs(r["Campos correctos"] - 5 / 6) < 1e-9
    r = calif["calificar"](["no sé"], fila)
    assert r["JSON válido"] == 0 and r["Campos correctos"] == 0


# ------------------------------------------------------------------ laptop (Ollama)
def test_ticket_py_usa_el_prompt_del_notebook():
    ns_nb, ns_py = {}, {}
    src = next(s for t, s in celdas(SOLUCION) if t == "code" and 'PROMPT = """' in s)
    exec("import json\n" + src, ns_nb)
    exec((TALLER / "solucion" / "ticket.py").read_text(encoding="utf-8").split("def ticket(")[0], ns_py)
    assert ns_py["PROMPT"] == ns_nb["PROMPT"]
    assert (TALLER / "inicio" / "ticket.py").read_text() == (TALLER / "solucion" / "ticket.py").read_text()


def test_modelfile_y_bloques_de_archivo():
    modelfile = (TALLER / "solucion" / "Modelfile").read_text(encoding="utf-8")
    assert modelfile.startswith("FROM ./") and "RENDERER gemma4" in modelfile
    md = CODELAB.read_text(encoding="utf-8")
    assert modelfile.strip() in md
