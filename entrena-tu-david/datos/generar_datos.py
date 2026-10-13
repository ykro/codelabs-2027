# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.30"]
# ///
"""Genera el dataset de Ferretería La Ceiba: mensajes de WhatsApp → ticket JSON.

Cómo funciona (detalle en DATOS.md):
  1. El código sortea el ticket (la respuesta correcta) a partir del catálogo y las reglas de la tienda.
  2. Gemini escribe un mensaje informal de cliente que expresa ese ticket, con las frases que el código le pide.
  3. Reglas en código validan cada mensaje; lo que no pasa se descarta.
  4. Train y test salen de sorteos con semillas distintas y se quitan duplicados entre ellos.

    GOOGLE_CLOUD_PROJECT=<tu-proyecto> uv run datos/generar_datos.py --train 1000 --test 150

Usa Gemini en Vertex AI con las credenciales de gcloud (ADC); no lleva llaves en el código.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FECHA = time.strftime("%Y-%m-%d")

# --------------------------------------------------------------------------------------------
# Catálogo y reglas de la tienda (lo que el modelo ajustado debe aprender)
# --------------------------------------------------------------------------------------------
TIPOS = ["pedido", "cotizacion", "reclamo", "seguimiento"]
CATEGORIAS = ["obra_gris", "techos", "plomeria", "electricidad", "pintura", "herramientas", "jardin"]
URGENCIAS = ["alta", "media", "baja"]
CAMPOS = ["tipo", "categoria", "producto", "cantidad", "monto_q", "urgencia"]

# producto (nombre en el catálogo), categoría de la tienda, palabras con que lo piden, precio unitario (Q)
CATALOGO = [
    ("cemento", "obra_gris", ["cemento"], (75, 90)),
    ("block", "obra_gris", ["block", "blocks", "bloque", "bloques"], (4, 6)),
    ("varilla 3/8", "obra_gris", ["varilla de 3/8", "varillas de 3/8", "hierro de 3/8", "varilla de tres octavos", "varillas de tres octavos", "hierro de tres octavos"], (40, 50)),
    ("arena de río", "obra_gris", ["arena"], (180, 250)),
    ("piedrín", "obra_gris", ["piedrin"], (250, 320)),
    ("cal hidratada", "obra_gris", ["cal"], (35, 50)),
    ("clavo de 3 pulgadas", "obra_gris", ["clavos de 3", "clavos de tres", "clavo de 3", "clavo de tres"], (8, 12)),
    ("alambre de amarre", "obra_gris", ["alambre de amarre"], (9, 12)),
    ("lámina de zinc", "techos", ["lamina", "laminas"], (85, 140)),
    ("costanera", "techos", ["costanera", "costaneras"], (60, 90)),
    ("tornillo para lámina", "techos", ["tornillo para lamina", "tornillos para lamina", "tornillo de lamina", "tornillos de lamina", "tornillos punta broca", "tornillo punta broca"], (1, 2)),
    ("canal para lluvia", "techos", ["canal", "canales"], (90, 150)),
    ("tubo pvc 1/2", "plomeria", ["tubo de 1/2", "tubos de 1/2", "tubo pvc de 1/2", "tubos pvc de 1/2", "tubo de media", "tubos de media", "tubo pvc de media", "tubos pvc de media"], (25, 40)),
    ("codo pvc 1/2", "plomeria", ["codo", "codos"], (3, 6)),
    ("llave de paso", "plomeria", ["llave de paso", "llaves de paso"], (35, 60)),
    ("pegamento pvc", "plomeria", ["pegamento", "pega para tubo"], (25, 45)),
    ("cinta teflón", "plomeria", ["teflon"], (5, 10)),
    ("tinaco", "plomeria", ["tinaco", "tinacos", "deposito de agua"], (900, 1800)),
    ("flotador", "plomeria", ["flotador", "flotadores"], (30, 60)),
    ("cable calibre 12", "electricidad", ["cable 12", "cable calibre 12", "cable del 12", "alambre electrico"], (6, 9)),
    ("foco led", "electricidad", ["foco", "focos", "bombillo", "bombillos"], (15, 35)),
    ("tomacorriente", "electricidad", ["tomacorriente", "tomacorrientes", "toma corriente", "enchufe", "enchufes"], (15, 30)),
    ("flipón", "electricidad", ["flipon", "flipones", "breaker", "breakers"], (45, 90)),
    ("cinta de aislar", "electricidad", ["cinta de aislar", "tape"], (6, 12)),
    ("apagador", "electricidad", ["apagador", "apagadores", "switch"], (15, 30)),
    ("pintura de agua", "pintura", ["pintura de agua", "latex"], (90, 180)),
    ("pintura de aceite", "pintura", ["pintura de aceite", "esmalte"], (150, 250)),
    ("brocha", "pintura", ["brocha", "brochas"], (10, 35)),
    ("rodillo", "pintura", ["rodillo", "rodillos"], (25, 50)),
    ("thinner", "pintura", ["thinner", "tiner", "diluyente"], (60, 90)),
    ("masilla", "pintura", ["masilla"], (40, 70)),
    ("martillo", "herramientas", ["martillo", "martillos"], (45, 90)),
    ("carretilla", "herramientas", ["carretilla", "carretillas"], (350, 600)),
    ("pala", "herramientas", ["pala", "palas"], (60, 110)),
    ("cinta métrica", "herramientas", ["cinta metrica", "flexometro"], (25, 60)),
    ("taladro", "herramientas", ["taladro", "taladros"], (350, 900)),
    ("serrucho", "herramientas", ["serrucho", "serruchos"], (50, 100)),
    ("manguera", "jardin", ["manguera", "mangueras"], (80, 200)),
    ("machete", "jardin", ["machete", "machetes"], (40, 80)),
    ("azadón", "jardin", ["azadon", "azadones"], (70, 120)),
    ("fertilizante", "jardin", ["fertilizante", "abono"], (5, 10)),
    ("aspersor", "jardin", ["aspersor", "aspersores"], (25, 60)),
    ("tijera de podar", "jardin", ["tijera de podar", "tijeras de podar"], (60, 120)),
]
PRODUCTOS = {p: (cat, kws, precio) for p, cat, kws, precio in CATALOGO}

# Regla de urgencia de la tienda: alta = hoy o emergencia; media = con fecha en los próximos días; baja = sin fecha.
SENALES_URGENCIA = {
    "alta": ["para hoy", "hoy mismo", "ahorita mismo", "urgente", "lo antes posible", "la obra esta parada",
             "tengo una fuga", "me quede sin luz", "es una emergencia"],
    "media": ["para manana", "pasado manana", "para el sabado", "para el lunes", "esta semana",
              "antes del viernes", "para el fin de semana", "para el jueves"],
    "baja": ["sin prisa", "cuando pueda", "solo estoy cotizando", "para el otro mes", "no hay apuro",
             "mas adelante", "con calma", "no es urgente"],
}
# Señales que solo tienen sentido con ciertos tipos o categorías (una fuga es de agua; sin luz, de electricidad).
SOLO_SI = {
    "solo estoy cotizando": {"tipo": ["cotizacion"]},
    "tengo una fuga": {"categoria": ["plomeria", "jardin"]},
    "me quede sin luz": {"categoria": ["electricidad"]},
    "la obra esta parada": {"categoria": ["obra_gris", "techos", "herramientas", "plomeria", "electricidad"]},
}
# Palabras que delatan una situación y por eso deben cuadrar con el ticket.
COHERENCIA = [
    ("cotiz", "tipo", ["cotizacion"]),
    ("fuga", "categoria", ["plomeria", "jardin"]),
    ("sin luz", "categoria", ["electricidad"]),
    ("se fue la luz", "categoria", ["electricidad"]),
    ("gote", "categoria", ["plomeria", "jardin", "techos"]),
]


def senales_posibles(t: dict) -> list[str]:
    """Frases de urgencia del nivel del ticket que tienen sentido con su tipo y categoría."""
    def cabe(frase):
        regla = SOLO_SI.get(frase, {})
        return all(t[campo] in valores for campo, valores in regla.items())
    return [f for f in SENALES_URGENCIA[t["urgencia"]] if cabe(f)]


# Palabras que no pueden aparecer en un mensaje de otro nivel (evitan señales mezcladas).
DIAS = ["manana", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo", "semana"]
PROHIBIDAS = {
    "alta": DIAS + ["sin prisa", "apuro", "calma", "cuando pueda", "mas adelante", "otro mes"],
    "media": ["hoy", "ahorita", "urge", "urgente", "urgencia", "emergencia", "ya mismo", "inmediat", "rapido",
              "sin prisa", "apuro", "calma", "cuando pueda", "mas adelante", "otro mes", "no es urgente"],
    "baja": DIAS + ["hoy", "ahorita", "urge", "emergencia", "ya mismo", "inmediat", "rapido", "parada", "fuga"],
}
# Palabras que delatan cada tipo (al menos una debe aparecer).
SENALES_TIPO = {
    "pedido": ["quiero", "necesito", "me manda", "me mandan", "me lleva", "me llevan", "aparte", "apart", "encarg",
               "pedido", "envi", "traig", "trae", "traer", "podria", "mand", "despach", "reserv", "llev", "compr", "requiero", "me hace",
               "pedir", "pido", "me despacha", "deme", "me da", "me vende", "ocupo", "quisiera", "mandeme", "llevar"],
    "cotizacion": ["cuanto", "precio", "cotiz", "sale", "vale", "cuesta", "costo", "tienen", "hay", "alcanza", "a como", "existencia", "consult", "?"],
    "reclamo": ["malo", "mala", "quebr", "rot", "no sirve", "no funciona", "no funciono", "fall", "de mas", "cobraron",
                "defect", "clavo", "doblad", "inservible", "quemad", "soluci", "arregl", "devol", "cambiar", "cambio", "reclamo", "no prende", "gote", "rajad", "incomplet", "falt"],
    "seguimiento": ["pedido", "llega", "llegado", "camino", "entrega", "ya pague", "deposit", "cuando", "despach",
                    "orden", "compra", "esperando", "todavia", "aun no", "envio", "como va", "que paso", "pague", "pagado"],
}
ESTILO = ["usa «vos»", "trata de usted", "escribe sin tildes", "usa abreviaturas de chat (q, xq, tmb)",
          "empieza con «Buenas»", "empieza con «Fíjese que»", "usa «va pues»", "usa «cabal»", "usa «chilero»",
          "usa «chunche»", "usa «patojo»", "usa «puchis»", "usa «a la gran»", "usa «mire»", "todo en minúsculas",
          "incluye un emoji", "mensaje muy corto", "mensaje de dos frases", "menciona para qué es (casa, obra, finca)"]

NUMEROS = {1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho",
           9: "nueve", 10: "diez", 11: "once", 12: "doce", 15: "quince", 20: "veinte", 25: "veinticinco",
           30: "treinta", 40: "cuarenta", 50: "cincuenta"}


def normalizar(texto: str) -> str:
    """minúsculas, sin tildes, espacios simples."""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def contiene(texto_norm: str, frase: str) -> bool:
    frase = normalizar(frase)
    if frase == "?":
        return "?" in texto_norm
    return re.search(rf"(?<![a-z0-9]){re.escape(frase)}(?![a-z0-9])", texto_norm) is not None


def contiene_raiz(texto_norm: str, raiz: str) -> bool:
    raiz = normalizar(raiz)
    if raiz == "?":
        return "?" in texto_norm
    return re.search(rf"(?<![a-z0-9]){re.escape(raiz)}", texto_norm) is not None


# --------------------------------------------------------------------------------------------
# 1. Sorteo del ticket (la respuesta correcta se decide antes de escribir el mensaje)
# --------------------------------------------------------------------------------------------
def frase_cantidad(rng: random.Random, n: int) -> str:
    especiales = {12: "una docena", 6: "media docena", 2: "un par", 100: "un ciento", 24: "dos docenas"}
    if n in especiales and rng.random() < 0.6:
        return especiales[n]
    if n == 1:
        return rng.choice(["un", "una", "1"])
    if n in NUMEROS and rng.random() < 0.35:
        return NUMEROS[n]
    return str(n)


def frase_monto(rng: random.Random, monto: float) -> str:
    entero = float(monto).is_integer()
    base = f"{int(monto):,}" if entero else f"{monto:,.2f}"
    if entero and monto >= 1000 and rng.random() < 0.5:
        base = str(int(monto))
    formas = ["Q{m}", "Q{m}", "Q {m}", "Q.{m}", "{m} quetzales"]
    if entero:
        formas += ["{m} varos", "{m} pesos", "{m} quetzalitos", "{m} quetzales"]
    forma = rng.choice(formas)
    return forma.format(m=base)


def sortear_ticket(rng: random.Random) -> dict:
    tipo = rng.choices(TIPOS, weights=[40, 25, 20, 15])[0]
    producto = rng.choice(list(PRODUCTOS))
    categoria, _, (pmin, pmax) = PRODUCTOS[producto]
    # cantidad
    if tipo in ("pedido", "cotizacion"):
        cantidad = rng.choice([1, 1, 2, 3, 4, 5, 6, 8, 10, 12, 12, 15, 20, 24, 25, 30, 40, 50, 100, 6, 2])
    elif tipo == "reclamo":
        cantidad = rng.choice([None, None, 1, 1, 2, 3, 5, 10])
    else:
        cantidad = rng.choice([None, None, None, 2, 5, 10, 20])
    if tipo == "cotizacion" and rng.random() < 0.25:
        cantidad = None
    # monto
    prob_monto = {"pedido": 0.3, "cotizacion": 0.15, "reclamo": 0.55, "seguimiento": 0.6}[tipo]
    monto = None
    if rng.random() < prob_monto:
        unidades = cantidad or rng.choice([1, 2, 5, 10])
        monto = round(unidades * rng.uniform(pmin, pmax))
        monto = max(5, int(round(monto / 5.0) * 5))
        if rng.random() < 0.1:
            monto = monto + 0.5
    urg_pesos = {"pedido": [35, 45, 20], "cotizacion": [10, 30, 60], "reclamo": [45, 35, 20], "seguimiento": [40, 40, 20]}[tipo]
    urgencia = rng.choices(URGENCIAS, weights=urg_pesos)[0]
    return {"tipo": tipo, "categoria": categoria, "producto": producto, "cantidad": cantidad,
            "monto_q": monto, "urgencia": urgencia}


def sortear_pistas(rng: random.Random, t: dict) -> dict:
    _, kws, _ = PRODUCTOS[t["producto"]]
    return {
        "producto_como": kws,
        "cantidad_como": frase_cantidad(rng, t["cantidad"]) if t["cantidad"] is not None else None,
        "monto_como": frase_monto(rng, t["monto_q"]) if t["monto_q"] is not None else None,
        "urgencia_como": rng.choice(senales_posibles(t)),
        "estilo": rng.sample(ESTILO, k=rng.choice([1, 2, 2, 3])),
    }


# --------------------------------------------------------------------------------------------
# 2. Gemini escribe el mensaje
# --------------------------------------------------------------------------------------------
INSTRUCCIONES = """Escribes mensajes de WhatsApp de clientes guatemaltecos a «Ferretería La Ceiba».
Para cada especificación escribe UN mensaje natural, informal, como lo escribiría una persona de Guatemala.
Reglas:
- El mensaje expresa el tipo de solicitud indicado:
  pedido = quiere comprar o que le lleven algo; cotizacion = pregunta precio o disponibilidad;
  reclamo = algo salió mal con una compra (producto malo, cobro de más, faltó algo);
  seguimiento = pregunta por un pedido o pago que ya hizo.
- Nombra el producto con una de las palabras de «producto_como» (en singular o plural según la cantidad).
- Si hay «cantidad_como», escribe esa cantidad tal cual, refiriéndose al producto. Si es null, no menciones ninguna cantidad.
- Si hay «monto_como», escribe ese monto tal cual (como dinero que pagó, le cobraron, tiene o quiere gastar). Si es null, no menciones dinero.
- Incluye textualmente la frase de «urgencia_como». No uses otras frases de tiempo o prisa.
- No escribas ningún otro número (ni teléfonos, ni horas, ni fechas con números, ni medidas extra).
- No menciones otros productos. No firmes con nombre.
- Sigue el «estilo». Máximo 250 caracteres.
Devuelve un arreglo JSON con objetos {"id": ..., "mensaje": ...} en el mismo orden."""


def cliente():
    from google import genai

    proyecto = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not proyecto:
        sys.exit("Define GOOGLE_CLOUD_PROJECT (proyecto con Vertex AI habilitado).")
    return genai.Client(vertexai=True, project=proyecto, location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"))


def escribir_mensajes(gc, specs: list[dict]) -> dict[str, str]:
    from google.genai import types

    pedido = [{"id": s["id"], "tipo": s["ticket"]["tipo"], **{k: v for k, v in s["pistas"].items()}} for s in specs]
    esquema = types.Schema(type="ARRAY", items=types.Schema(
        type="OBJECT", properties={"id": types.Schema(type="STRING"), "mensaje": types.Schema(type="STRING")},
        required=["id", "mensaje"]))
    for intento in range(4):
        try:
            r = gc.models.generate_content(
                model=MODELO,
                contents=INSTRUCCIONES + "\n\nEspecificaciones:\n" + json.dumps(pedido, ensure_ascii=False, indent=1),
                config=types.GenerateContentConfig(temperature=1.0, response_mime_type="application/json",
                                                   response_schema=esquema),
            )
            return {o["id"]: o["mensaje"].strip() for o in json.loads(r.text)}
        except Exception as e:  # noqa: BLE001 — reintenta errores transitorios de la API
            print(f"  reintento {intento + 1}: {str(e)[:120]}", file=sys.stderr)
            time.sleep(5 * (intento + 1))
    return {}


# --------------------------------------------------------------------------------------------
# 3. Validación por reglas
# --------------------------------------------------------------------------------------------
def numeros_en(texto: str) -> list[float]:
    """Números escritos con dígitos (acepta 1,250 y 350.50)."""
    return [float(m.group(0).replace(",", "")) for m in re.finditer(r"\d+(?:,\d{3})*(?:\.\d+)?", texto)]


def validar(mensaje: str, ticket: dict, pistas: dict) -> list[str]:
    """Devuelve la lista de reglas que el mensaje no cumple (vacía = válido)."""
    fallas = []
    n = normalizar(mensaje)
    if not 25 <= len(mensaje) <= 300:
        fallas.append("largo")
    # producto: la frase pedida aparece y ningún otro producto aparece
    usadas = [k for k in pistas["producto_como"] if contiene(n, k)]
    if not usadas:
        fallas.append("producto")
    resto = n
    for k in sorted(usadas, key=len, reverse=True):
        resto = re.sub(rf"(?<![a-z0-9]){re.escape(normalizar(k))}(?![a-z0-9])", " ", resto)
    for otro, (_, kws, _) in PRODUCTOS.items():
        if otro != ticket["producto"] and any(contiene(resto, k) for k in kws):
            fallas.append(f"otro_producto:{otro}")
            break
    # cantidad
    if pistas["cantidad_como"] and not contiene(n, pistas["cantidad_como"]):
        fallas.append("cantidad")
    # monto: el número aparece
    permitidos = {float(x) for x in re.findall(r"\d+", ticket["producto"])} | {0.5, 0.375}
    if ticket["cantidad"] is not None:
        permitidos.add(float(ticket["cantidad"]))
    if ticket["monto_q"] is not None:
        permitidos.add(float(ticket["monto_q"]))
        if float(ticket["monto_q"]) not in numeros_en(mensaje):
            fallas.append("monto")
    otros = [x for x in numeros_en(mensaje) if x not in permitidos]
    if otros:
        fallas.append(f"numero_extra:{otros[0]:g}")
    if ticket["monto_q"] is None and re.search(r"\b(q\.?\s?\d|quetzal|varos|pesos|pisto)", n):
        fallas.append("dinero_sin_monto")
    # urgencia: la señal pedida aparece y ninguna de otro nivel
    if not contiene(n, pistas["urgencia_como"]):
        fallas.append("urgencia")
    sin_senal = n.replace(normalizar(pistas["urgencia_como"]), " ")
    if ticket["urgencia"] == "baja":
        sin_senal = sin_senal.replace("no es urgente", " ")
    for p in PROHIBIDAS[ticket["urgencia"]]:
        if contiene_raiz(sin_senal, p):
            fallas.append(f"urgencia_mezclada:{p}")
            break
    # coherencia: lo que dice el mensaje cuadra con el tipo y la categoría
    for raiz, campo, valores in COHERENCIA:
        if contiene_raiz(n, raiz) and ticket[campo] not in valores:
            fallas.append(f"incoherente:{raiz}")
            break
    # tipo: al menos una palabra del tipo
    if not any(contiene_raiz(n, s) for s in SENALES_TIPO[ticket["tipo"]]):
        fallas.append("tipo")
    return fallas


def validar_ticket(t: dict) -> list[str]:
    """Reglas del esquema (sirven para el dataset y para calificar respuestas)."""
    f = []
    if set(t) != set(CAMPOS):
        f.append("campos")
    if t.get("tipo") not in TIPOS:
        f.append("tipo")
    if t.get("categoria") not in CATEGORIAS:
        f.append("categoria")
    if t.get("urgencia") not in URGENCIAS:
        f.append("urgencia")
    if not isinstance(t.get("producto"), str) or not t.get("producto"):
        f.append("producto")
    c = t.get("cantidad")
    if c is not None and (not isinstance(c, int) or isinstance(c, bool) or c <= 0):
        f.append("cantidad")
    m = t.get("monto_q")
    if m is not None and (not isinstance(m, (int, float)) or isinstance(m, bool) or m <= 0):
        f.append("monto_q")
    return f


# --------------------------------------------------------------------------------------------
# 4. Armar train y test
# --------------------------------------------------------------------------------------------
def generar(split: str, objetivo: int, semilla: int, gc, vistos: set[str], lote: int = 15) -> tuple[list[dict], dict]:
    rng = random.Random(semilla)
    registros, rechazos, pedidos = [], {}, 0
    while len(registros) < objetivo:
        faltan = objetivo - len(registros)
        specs = []
        for _ in range(int(faltan * 1.3) + 5):
            pedidos += 1
            t = sortear_ticket(rng)
            specs.append({"id": f"{split}-{semilla}-{pedidos:05d}", "ticket": t, "pistas": sortear_pistas(rng, t)})
        lotes = [specs[i:i + lote] for i in range(0, len(specs), lote)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            respuestas = list(ex.map(lambda l: escribir_mensajes(gc, l), lotes))
        for grupo, resp in zip(lotes, respuestas):
            for s in grupo:
                msg = resp.get(s["id"])
                if not msg:
                    rechazos["sin_respuesta"] = rechazos.get("sin_respuesta", 0) + 1
                    continue
                fallas = validar(msg, s["ticket"], s["pistas"]) + validar_ticket(s["ticket"])
                clave = normalizar(msg)
                if clave in vistos:
                    fallas.append("duplicado")
                if fallas:
                    if os.environ.get("VER_RECHAZOS"):
                        print(f"  ✗ {fallas} {s['ticket']['tipo']}: {msg}", file=sys.stderr)
                    k = fallas[0].split(":")[0]
                    rechazos[k] = rechazos.get(k, 0) + 1
                    continue
                vistos.add(clave)
                registros.append({
                    "id": f"{split}-{len(registros) + 1:04d}",
                    "mensaje": msg,
                    "ticket": s["ticket"],
                    "origen": {"tipo": "sintetico", "modelo": MODELO, "servicio": "Vertex AI", "fecha": FECHA,
                               "semilla": semilla, "solicitud": s["id"], "pistas": s["pistas"],
                               "validacion": "reglas de generar_datos.py: ok"},
                })
                if len(registros) >= objetivo:
                    break
            if len(registros) >= objetivo:
                break
        print(f"{split}: {len(registros)}/{objetivo} válidos, {pedidos} solicitados, rechazos {rechazos}", file=sys.stderr)
    return registros, {"solicitados": pedidos, "validos": len(registros), "rechazos": rechazos}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=900)
    ap.add_argument("--test", type=int, default=150)
    ap.add_argument("--salida", default=str(AQUI))
    a = ap.parse_args()
    gc = cliente()
    vistos: set[str] = set()
    # El test se genera primero y con otra semilla: nunca se usa para entrenar.
    test, est_test = generar("test", a.test, 2027, gc, vistos)
    train, est_train = generar("train", a.train, 1821, gc, vistos)
    out = Path(a.salida)
    for nombre, filas in (("train.jsonl", train), ("test.jsonl", test)):
        with open(out / nombre, "w", encoding="utf-8") as f:
            for r in filas:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump({"modelo": MODELO, "fecha": FECHA, "train": est_train, "test": est_test},
              open(out / "estadisticas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"train": est_train, "test": est_test}, ensure_ascii=False))


if __name__ == "__main__":
    main()
