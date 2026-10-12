"""HTML de las páginas para personas (aprobación y agenda). Ya viene completo."""

from html import escape

ESTILO = """
:root { --tinta:#1c1d21; --suave:#5b5f6b; --borde:#e3e5ea; --fondo:#f6f6f3; --lava:#c2410c;
        --ok:#15803d; --ok-fondo:#ecfdf3; --no:#b42318; --no-fondo:#fef3f2; --pend:#a15c07; --pend-fondo:#fffaeb; }
* { box-sizing: border-box; }
body { margin:0; background:var(--fondo); color:var(--tinta);
       font:16px/1.5 Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width:480px; margin:0 auto; padding:20px 16px 40px; }
.marca { display:flex; align-items:center; gap:10px; font-weight:700; font-size:17px; margin-bottom:18px; }
.marca span { display:grid; place-items:center; width:36px; height:36px; border-radius:10px;
              background:var(--lava); color:#fff; font-size:18px; }
.tarjeta { background:#fff; border:1px solid var(--borde); border-radius:16px; padding:20px; }
h1 { font-size:22px; line-height:1.25; margin:0 0 6px; }
p { margin:0 0 12px; }
.suave { color:var(--suave); font-size:15px; }
dl { display:grid; grid-template-columns:auto 1fr; gap:10px 16px; margin:18px 0; }
dt { color:var(--suave); font-size:15px; }
dd { margin:0; font-weight:600; text-align:right; }
.estado { display:inline-block; padding:4px 10px; border-radius:999px; font-size:14px; font-weight:700; }
.PENDIENTE { background:var(--pend-fondo); color:var(--pend); }
.CONFIRMADA { background:var(--ok-fondo); color:var(--ok); }
.RECHAZADA { background:var(--no-fondo); color:var(--no); }
form { display:grid; gap:10px; margin-top:8px; }
button { min-height:52px; border-radius:12px; font-family:inherit; font-size:17px; font-weight:600; cursor:pointer; }
.aprobar { background:var(--ok); color:#fff; border:0; }
.rechazar { background:#fff; color:var(--no); border:1px solid #f1b8b2; }
.aviso { margin-top:16px; padding:12px 14px; border-radius:12px; background:var(--ok-fondo); color:#064e2b; font-size:15px; }
.aviso.no { background:var(--no-fondo); color:#7a1a12; }
ul { list-style:none; padding:0; margin:0; display:grid; gap:10px; }
li a { display:block; text-decoration:none; color:inherit; background:#fff; border:1px solid var(--borde);
       border-radius:14px; padding:14px 16px; }
li .fila { display:flex; justify-content:space-between; gap:12px; align-items:center; }
code { font-family:"JetBrains Mono", ui-monospace, monospace; font-size:14px; }
"""


def _pagina(titulo: str, cuerpo: str) -> str:
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{escape(titulo)} · Taller Volcán</title>
<style>{ESTILO}</style></head>
<body><main><div class="marca"><span>▲</span>Taller Volcán</div>{cuerpo}</main></body></html>"""


def aprobacion(cita: dict) -> str:
    estado = cita["estado"]
    filas = f"""<dl>
<dt>Servicio</dt><dd>{escape(cita["servicio"])}</dd>
<dt>Día</dt><dd>{escape(cita["dia"])}</dd>
<dt>Hora</dt><dd>{escape(cita["hora"])}</dd>
<dt>Precio</dt><dd>Q{cita["precio_q"]:,.2f}</dd>
<dt>Solicitud</dt><dd><code>{escape(cita["id"])}</code></dd>
</dl>"""
    if estado == "PENDIENTE":
        final = """<form method="post">
<button class="aprobar" name="decision" value="aprobar">Aprobar cita</button>
<button class="rechazar" name="decision" value="rechazar">Rechazar</button>
</form>"""
    elif estado == "CONFIRMADA":
        final = '<p class="aviso">Cita confirmada. Vuelve con el asistente y dile «ya aprobé».</p>'
    else:
        final = '<p class="aviso no">Rechazaste esta solicitud. El horario quedó libre otra vez.</p>'
    return _pagina("Aprobar cita", f"""<section class="tarjeta">
<p><span class="estado {estado}">{estado}</span></p>
<h1>Un asistente pidió esta cita por ti</h1>
<p class="suave">Nada queda agendado hasta que tú lo apruebes aquí.</p>
{filas}{final}</section>""")


def agenda(citas: list[dict]) -> str:
    if not citas:
        lista = '<p class="suave">Todavía no hay solicitudes. Pídele una cita al agente.</p>'
    else:
        items = "".join(
            f"""<li><a href="/aprobar/{escape(c["id"])}"><div class="fila"><strong>{escape(c["servicio"])}</strong>
<span class="estado {c["estado"]}">{c["estado"]}</span></div>
<span class="suave">{escape(c["dia"])} · {escape(c["hora"])} · <code>{escape(c["id"])}</code></span></a></li>"""
            for c in sorted(citas, key=lambda c: (c["fecha"], c["hora"]))
        )
        lista = f"<ul>{items}</ul>"
    return _pagina("Agenda", f"""<h1>Agenda</h1>
<p class="suave">Solicitudes que hicieron los agentes. Datos en memoria: se borran al reiniciar el servidor.</p>{lista}""")


def no_existe(cita_id: str) -> str:
    return _pagina("No existe", f"""<section class="tarjeta"><h1>No encontramos esa solicitud</h1>
<p class="suave">La solicitud <code>{escape(cita_id)}</code> no existe. Si reiniciaste el servidor, la agenda se borró:
pide la cita otra vez.</p></section>""")
