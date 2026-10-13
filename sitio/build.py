# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.6", "pygments>=2.18", "pyyaml>=6"]
# ///
"""Genera el sitio de los codelabs: un HTML por taller más un índice.

    uv run sitio/build.py            # escribe sitio/dist/
    uv run sitio/build.py --check    # además falla si algo quedó mal enlazado
    uv run sitio/build.py --excluir entrena-tu-david   # omite un taller que aún no está listo

Formato de cada codelab.md:

    ---
    titulo: ...
    charla: ...
    resumen: ...
    duracion: 75
    referencia: https://...        (opcional)
    ---

    ## Título del paso | 10         (minutos)

    :::tip Título opcional
    Texto en Markdown.
    :::

    ```python
    código (se resalta con Pygments al generar, sin JavaScript)
    ```

    ```salida
    lo que el alumno debe ver en su terminal
    ```
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "sitio" / "dist"
TALLERES = ["entrena-tu-david", "agente-mcp", "tienda-para-agentes", "gemma-en-el-navegador"]

ETIQUETAS = {
    "bash": "Terminal", "shell": "Terminal", "sh": "Terminal", "console": "Terminal",
    "python": "Python", "py": "Python", "javascript": "JavaScript", "js": "JavaScript",
    "html": "HTML", "json": "JSON", "toml": "TOML", "yaml": "YAML", "css": "CSS",
    "text": "Texto", "salida": "Salida esperada", "jsonl": "JSONL", "xml": "XML",
}
CALLOUTS = {"info": "Para saber", "tip": "Consejo", "warn": "Atención", "check": "Comprueba"}


class Estilo(HtmlFormatter):
    pass


def resaltar(codigo: str, lenguaje: str) -> str:
    lenguaje = (lenguaje or "text").lower()
    etiqueta = ETIQUETAS.get(lenguaje, lenguaje.upper())
    if lenguaje == "salida":
        cuerpo = f'<pre class="salida"><code>{html.escape(codigo)}</code></pre>'
        return f'<figure class="bloque bloque-salida"><figcaption><span>{etiqueta}</span></figcaption>{cuerpo}</figure>'
    nombre = {"jsonl": "json", "console": "bash", "sh": "bash", "shell": "bash"}.get(lenguaje, lenguaje)
    try:
        lexer = get_lexer_by_name(nombre)
    except ClassNotFound:
        lexer = TextLexer()
    cuerpo = highlight(codigo, lexer, HtmlFormatter(nowrap=True))
    return (
        f'<figure class="bloque"><figcaption><span>{etiqueta}</span>'
        f'<button class="copiar" type="button" aria-label="Copiar código">Copiar</button></figcaption>'
        f'<pre class="hl"><code>{cuerpo}</code></pre></figure>'
    )


def leer(md_path: Path) -> tuple[dict, list[dict]]:
    texto = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        raise SystemExit(f"{md_path}: falta el encabezado YAML")
    meta = yaml.safe_load(m.group(1))
    cuerpo = texto[m.end():]
    pasos = []
    for bloque in re.split(r"^## ", cuerpo, flags=re.M)[1:]:
        cabecera, _, contenido = bloque.partition("\n")
        titulo, _, minutos = cabecera.partition("|")
        pasos.append({"titulo": titulo.strip(), "minutos": int(minutos.strip() or 0), "md": contenido})
    return meta, pasos


def convertir(md: str) -> str:
    """Markdown → HTML con bloques de código y avisos ya procesados."""
    guardados: list[str] = []

    def guardar(fragmento: str) -> str:
        guardados.append(fragmento)
        return f"\n\nXBLOQUE{len(guardados) - 1}X\n\n"

    def codigo(m: re.Match) -> str:
        return guardar(resaltar(m.group(3).rstrip("\n"), m.group(2)))

    md = re.sub(r"^(?P<i>[ \t]*)```([\w+-]*)[^\n]*\n(.*?)^[ \t]*```[ \t]*$", codigo, md, flags=re.M | re.S)

    def aviso(m: re.Match) -> str:
        tipo = m.group(1)
        titulo = m.group(2).strip() or CALLOUTS.get(tipo, "")
        interior = convertir_simple(m.group(3))
        return guardar(
            f'<aside class="aviso aviso-{tipo}"><p class="aviso-titulo">{html.escape(titulo)}</p>{interior}</aside>'
        )

    md = re.sub(r"^:::(\w+)[ \t]*([^\n]*)\n(.*?)^:::[ \t]*$", aviso, md, flags=re.M | re.S)
    salida = convertir_simple(md)

    def restaurar(m: re.Match) -> str:
        return guardados[int(m.group(1))]

    for _ in range(3):
        salida = re.sub(r"<p>XBLOQUE(\d+)X</p>", restaurar, salida)
        salida = re.sub(r"XBLOQUE(\d+)X", restaurar, salida)
    return salida


def etiquetar_tabla(m: re.Match) -> str:
    """Envuelve la tabla y pone a cada celda el nombre de su columna, para apilarla como tarjetas en el teléfono."""
    tabla = m.group(0)
    columnas = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", tabla, re.S)]

    def fila(f: re.Match) -> str:
        celdas = iter(columnas)
        return re.sub(r"<td([^>]*)>", lambda c: f'<td{c.group(1)} data-col="{html.escape(next(celdas, ""), quote=True)}">', f.group(0))

    tabla = re.sub(r"<tr>.*?</tr>", fila, tabla, flags=re.S)
    return f'<div class="tabla">{tabla}</div>'


def convertir_simple(md: str) -> str:
    out = markdown.markdown(md, extensions=["tables", "sane_lists", "attr_list"], output_format="html")
    out = re.sub(r"<table>.*?</table>", etiquetar_tabla, out, flags=re.S)
    out = re.sub(r'<img ([^>]*)>', r'<img loading="lazy" \1>', out)
    out = re.sub(r'<a href="(https?://[^"]+)"', r'<a target="_blank" rel="noopener" href="\1"', out)
    return out


def pagina(slug: str, meta: dict, pasos: list[dict], plantilla: str) -> str:
    total = sum(p["minutos"] for p in pasos)
    nav = "\n".join(
        f'<li><a href="#paso-{i + 1}" data-paso="{i + 1}"><span class="num">{i + 1}</span>'
        f'<span class="t">{html.escape(p["titulo"])}</span></a></li>'
        for i, p in enumerate(pasos)
    )
    secciones = []
    for i, p in enumerate(pasos):
        anterior = f'<a class="btn sec" href="#paso-{i}">← Anterior</a>' if i else "<span></span>"
        siguiente = (
            f'<a class="btn" href="#paso-{i + 2}">Siguiente →</a>' if i + 1 < len(pasos)
            else '<a class="btn" href="index.html">Ver los otros talleres</a>'
        )
        minutos = f'<span class="min">{p["minutos"]} min</span>' if p["minutos"] else ""
        secciones.append(
            f'<section class="paso" id="paso-{i + 1}"><header><p class="n">Paso {i + 1} de {len(pasos)} {minutos}</p>'
            f'<h2>{html.escape(p["titulo"])}</h2></header>{convertir(p["md"])}'
            f'<nav class="pie">{anterior}{siguiente}</nav></section>'
        )
    referencia = meta.get("referencia")
    ref_html = (
        f'<a class="ref" target="_blank" rel="noopener" href="{html.escape(referencia)}">Ver el resultado final en línea ↗</a>'
        if referencia else ""
    )
    return (
        plantilla.replace("{{TITULO}}", html.escape(meta["titulo"]))
        .replace("{{CHARLA}}", html.escape(meta.get("charla", "")))
        .replace("{{RESUMEN}}", html.escape(meta.get("resumen", "")))
        .replace("{{DURACION}}", str(meta.get("duracion") or total))
        .replace("{{REFERENCIA}}", ref_html)
        .replace("{{NAV}}", nav)
        .replace("{{PASOS}}", "\n".join(secciones))
        .replace("{{TOTAL}}", str(len(pasos)))
        .replace("{{SLUG}}", slug)
    )


def indice(talleres: list[tuple[str, dict, list[dict]]], plantilla: str) -> str:
    tarjetas = []
    for slug, meta, pasos in talleres:
        tarjetas.append(
            f'<a class="tarjeta" href="{slug}.html"><p class="charla">{html.escape(meta.get("charla", ""))}</p>'
            f'<h2>{html.escape(meta["titulo"])}</h2><p>{html.escape(meta.get("resumen", ""))}</p>'
            f'<p class="meta">{len(pasos)} pasos · {meta.get("duracion")} min</p></a>'
        )
    return plantilla.replace("{{TARJETAS}}", "\n".join(tarjetas))


def main() -> None:
    check = "--check" in sys.argv
    excluir = {sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == "--excluir"}
    plantilla = (RAIZ / "sitio" / "plantilla.html").read_text(encoding="utf-8")
    plantilla_indice = (RAIZ / "sitio" / "indice.html").read_text(encoding="utf-8")
    estilos_codigo = HtmlFormatter(style="friendly").get_style_defs(".hl")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "codigo.css").write_text(estilos_codigo, encoding="utf-8")
    shutil.copy(RAIZ / "sitio" / "estilo.css", DIST / "estilo.css")
    shutil.copy(RAIZ / "sitio" / "app.js", DIST / "app.js")
    hechos = []
    errores = []
    for slug in TALLERES:
        md_path = RAIZ / slug / "codelab.md"
        if not md_path.exists() or slug in excluir:
            continue
        meta, pasos = leer(md_path)
        salida = pagina(slug, meta, pasos, plantilla)
        assets = RAIZ / slug / "assets"
        if assets.exists():
            shutil.copytree(assets, DIST / slug / "assets")
        salida = salida.replace('src="assets/', f'src="{slug}/assets/')
        for src in re.findall(r'src="([^"]+)"', salida):
            if not src.startswith("http") and not (DIST / src).exists():
                errores.append(f"{slug}: falta {src}")
        (DIST / f"{slug}.html").write_text(salida, encoding="utf-8")
        hechos.append((slug, meta, pasos))
    (DIST / "index.html").write_text(indice(hechos, plantilla_indice), encoding="utf-8")
    print(f"Sitio en {DIST.relative_to(RAIZ)}: {len(hechos)} talleres")
    if errores:
        print("\n".join(errores))
        if check:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
