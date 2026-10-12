"""Aplica los bloques de código del codelab sobre inicio/, como lo haría el alumno.

Cada bloque que el alumno pega lleva en su encabezado `archivo=RUTA todo=ID`:

    ```python archivo=ucp.py todo=perfil

En inicio/ ese lugar está marcado con una línea `TODO paso N (ID)`. En Python se
reemplaza desde esa línea hasta el siguiente `# TODO`, `# ---` o el final del
archivo; en plantillas HTML se reemplaza solo esa línea.

    python aplicar_codelab.py CODELAB.md CARPETA [--hasta N]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BLOQUE = re.compile(r"^## (?P<paso>[^\n|]+)\|[^\n]*$|^```(?P<lang>[\w+-]*)[ \t]+(?P<info>[^\n]*)\n(?P<codigo>.*?)^```[ \t]*$",
                    re.M | re.S)


def bloques(codelab: str) -> list[dict]:
    """Bloques con archivo= y todo=, en orden, con el número de paso (## …) donde aparecen."""
    salida, paso = [], 0
    for m in BLOQUE.finditer(codelab):
        if m.group("paso") is not None:
            paso += 1
            continue
        attrs = dict(re.findall(r"(\w+)=(\S+)", m.group("info")))
        if "archivo" in attrs:
            salida.append({"paso": paso, "archivo": attrs["archivo"], "todo": attrs.get("todo"),
                           "codigo": m.group("codigo").rstrip("\n")})
    return salida


def aplicar(bloque: dict, carpeta: Path) -> None:
    ruta = carpeta / bloque["archivo"]
    texto = ruta.read_text(encoding="utf-8")
    marca = re.search(rf"^.*TODO paso \d+ \({re.escape(bloque['todo'])}\).*$", texto, re.M)
    if marca is None:
        raise SystemExit(f"No encontré TODO ({bloque['todo']}) en {ruta}")
    if ruta.suffix == ".py":
        fin = re.compile(r"^# (TODO|---)", re.M).search(texto, marca.end())
        corte = fin.start() if fin else len(texto)
        cola = "\n\n\n" if fin else "\n"
        texto = texto[: marca.start()] + bloque["codigo"] + cola + texto[corte:]
    else:
        sangria = re.match(r"[ \t]*", marca.group(0)).group(0)
        nuevo = "\n".join(sangria + linea if linea else linea for linea in bloque["codigo"].split("\n"))
        texto = texto[: marca.start()] + nuevo + texto[marca.end():]
    ruta.write_text(texto, encoding="utf-8")


def main() -> None:
    codelab, carpeta = Path(sys.argv[1]), Path(sys.argv[2])
    hasta = int(sys.argv[sys.argv.index("--hasta") + 1]) if "--hasta" in sys.argv else 99
    desde = int(sys.argv[sys.argv.index("--desde") + 1]) if "--desde" in sys.argv else 0
    for b in bloques(codelab.read_text(encoding="utf-8")):
        if desde <= b["paso"] <= hasta and b["todo"]:
            aplicar(b, carpeta)
            print(f"paso {b['paso']}: {b['archivo']} ({b['todo']})")


if __name__ == "__main__":
    main()
