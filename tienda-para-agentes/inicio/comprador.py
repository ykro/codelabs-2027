"""Comprador: un agente de compras que habla UCP. Ya viene escrito; no lo editas.

    export GEMINI_API_KEY="tu-llave-de-ai-studio"
    uv run comprador.py http://localhost:8080
    uv run comprador.py http://localhost:8080 "otro encargo"

Usa Gemini una sola vez: para entender el encargo y elegir del catálogo. Todo lo
que toca dinero (precio, plazo, firma de la tienda) lo revisa el código. Nunca
completa la compra: se detiene en ready_for_complete y te da el enlace para que
la apruebes tú.
"""

from __future__ import annotations

import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

import ap2
from auditar import parse_html
from catalogo import fecha_larga, hoy_gt

ENCARGO = "250 g de café de Huehuetenango molido para prensa francesa, menos de Q120, que llegue esta semana"
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
PERFIL_COMPRADOR = os.environ.get(
    "PERFIL_COMPRADOR",
    "https://raw.githubusercontent.com/ykro/codelabs-2027/main/tienda-para-agentes/solucion/perfil_comprador.json",
)
ESPERA_MAXIMA = int(os.environ.get("ESPERA_MAXIMA", "600"))  # segundos esperando tu aprobación
LLAMADAS_GEMINI = 0


class Eleccion(BaseModel):
    sku: str = Field(description="sku exacto de la variante elegida, o cadena vacía si ninguna sirve")
    cantidad: int = Field(description="unidades de esa variante")
    total_menor_que_q: float = Field(description="el total (producto + envío) debe ser menor que este monto en quetzales")
    entregar_a_mas_tardar: str = Field(description="fecha límite de entrega, AAAA-MM-DD")
    razon: str = Field(description="una frase: por qué esa variante cumple el encargo")


def paso(numero: int, texto: str) -> None:
    print(f"\n[{numero}] {texto}")


def alto(texto: str) -> None:
    print(f"\n✗ {texto}")
    print(f"Llamadas a Gemini: {LLAMADAS_GEMINI}")
    sys.exit(1)


def leer_catalogo(http: httpx.Client, tienda: str) -> list[dict]:
    """Lee el sitemap y el JSON-LD de cada página de producto. Sin JavaScript, sin adivinar."""
    res = http.get(f"{tienda}/sitemap.xml")
    if res.status_code != 200:
        return []
    urls = [e.text.strip() for e in ET.fromstring(res.text).iter() if e.tag.endswith("loc") and e.text]
    variantes = []
    for url in urls[:20]:
        pagina = parse_html(http.get(url).text, url)
        for bloque in pagina["jsonld"]:
            for nodo in bloque if isinstance(bloque, list) else [bloque]:
                if not isinstance(nodo, dict) or nodo.get("@type") not in {"Product", "ProductGroup"}:
                    continue
                for v in nodo.get("hasVariant") or [nodo]:
                    oferta = v.get("offers") or {}
                    variantes.append({
                        "sku": v.get("sku"),
                        "nombre": v.get("name") or nodo.get("name"),
                        "precio": f"{oferta.get('priceCurrency')} {oferta.get('price')}",
                        "disponible": str(oferta.get("availability", "")).endswith("InStock"),
                    })
    return variantes


def elegir(encargo: str, variantes: list[dict], hoy: date) -> Eleccion:
    global LLAMADAS_GEMINI
    lista = "\n".join(
        f"- {v['sku']} | {v['nombre']} | {v['precio']} | {'disponible' if v['disponible'] else 'agotado'}"
        for v in variantes
    )
    prompt = (
        f"Eres un agente de compras. Hoy es {fecha_larga(hoy)} de {hoy.year} ({hoy.isoformat()}), hora de Guatemala; "
        "la semana termina el domingo.\n"
        f"Encargo de la persona: «{encargo}»\n\n"
        f"Catálogo de la tienda (sku | nombre | precio | disponibilidad):\n{lista}\n\n"
        "Elige la variante disponible que cumple el encargo. El presupuesto se refiere al total con envío. "
        "No inventes sku: copia uno de la lista."
    )
    cliente = genai.Client()  # lee GEMINI_API_KEY del entorno
    LLAMADAS_GEMINI += 1
    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Eleccion),
    )
    return Eleccion.model_validate_json(respuesta.text)


def total(checkout: dict) -> int:
    return next(t["amount"] for t in checkout["totals"] if t["type"] == "total")


def revisar_firma(checkout: dict, perfil: dict) -> None:
    if "ap2" not in checkout:
        print("  La tienda no firma sus checkouts (sin AP2).")
    elif ap2.verificar_firma(checkout, perfil.get("keys", [])):
        print("  Firma de la tienda verificada con la llave de /.well-known/ucp (AP2).")
    else:
        alto("La firma de la tienda no coincide con su llave publicada. No te muestro este checkout.")


def mejor_opcion(checkout: dict, eleccion: Eleccion) -> tuple[dict | None, list[str]]:
    """La opción de entrega más barata que llega a tiempo y respeta el presupuesto."""
    grupo = checkout["fulfillment"]["methods"][0]["groups"][0]
    actual = next(o for o in grupo["options"] if o["id"] == grupo["selected_option_id"])
    sin_envio = total(checkout) - actual["totals"][0]["amount"]
    limite = date.fromisoformat(eleccion.entregar_a_mas_tardar)
    validas, notas = [], []
    for opcion in grupo["options"]:
        llega = date.fromisoformat(opcion["latest_fulfillment_time"][:10])
        con_envio = sin_envio + opcion["totals"][0]["amount"]
        cumple = llega <= limite and con_envio < eleccion.total_menor_que_q * 100
        notas.append(f"  {'✓' if cumple else '✗'} {opcion['title']}: llega a más tardar el {fecha_larga(llega)}, "
                     f"total Q{con_envio / 100:.2f}")
        if cumple:
            validas.append((con_envio, opcion))
    return (min(validas, key=lambda x: x[0])[1] if validas else None), notas


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print('Uso: uv run comprador.py URL_DE_LA_TIENDA ["encargo"]')
        sys.exit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # cada línea sale aunque redirijas la salida
    tienda = args[0].rstrip("/")
    encargo = args[1] if len(args) > 1 else ENCARGO
    http = httpx.Client(timeout=20, headers={"UCP-Agent": f'profile="{PERFIL_COMPRADOR}"'})
    print(f"Encargo: «{encargo}»")

    paso(1, f"Descubro la tienda: {tienda}/.well-known/ucp")
    res = http.get(f"{tienda}/.well-known/ucp")
    if res.status_code != 200:
        alto("La tienda no publica un perfil UCP. Un agente no sabe cómo comprarle.")
    perfil = res.json()
    capacidades = perfil["ucp"].get("capabilities", {})
    servicio = next((s for s in perfil["ucp"]["services"].get("dev.ucp.shopping", []) if s.get("transport") == "rest"), None)
    if servicio is None or "dev.ucp.shopping.checkout" not in capacidades:
        alto("El perfil no declara checkout por REST.")
    endpoint = servicio["endpoint"]
    print(f"  UCP {perfil['ucp']['version']} · endpoint {endpoint}")
    print(f"  Capacidades: {', '.join(capacidades)}")

    paso(2, "Leo el catálogo estructurado (sitemap + JSON-LD)")
    variantes = leer_catalogo(http, tienda)
    if not variantes:
        alto("No encontré productos con datos estructurados.")
    print(f"  {len(variantes)} variantes, {sum(v['disponible'] for v in variantes)} disponibles")

    paso(3, f"Le pido a Gemini ({MODELO}) que elija según el encargo")
    hoy = hoy_gt()
    try:
        eleccion = elegir(encargo, variantes, hoy)
    except errors.APIError as e:
        if e.code == 429:
            alto("Gemini respondió 429: llegaste al límite de tu cuota gratuita. "
                 "Prueba con export GEMINI_MODEL=gemini-3.5-flash-lite o espera a mañana.")
        alto(f"Gemini respondió un error {e.code}: {e.message}")
    print(f"  Elige {eleccion.sku} × {eleccion.cantidad}: {eleccion.razon}")
    print(f"  Condiciones: total menor que Q{eleccion.total_menor_que_q:.2f}, "
          f"entrega a más tardar el {eleccion.entregar_a_mas_tardar}")
    elegida = next((v for v in variantes if v["sku"] == eleccion.sku and v["disponible"]), None)
    if elegida is None:
        alto(f"«{eleccion.sku}» no está en el catálogo o está agotado. No compro.")

    paso(4, "Creo la sesión de checkout")
    pedido = {"line_items": [{"item": {"id": eleccion.sku}, "quantity": eleccion.cantidad}]}
    checkout = http.post(f"{endpoint}/checkout-sessions", json=pedido).json()
    if "id" not in checkout:
        alto(f"La tienda rechazó el checkout: {checkout.get('messages')}")
    print(f"  {checkout['id']} · {checkout['status']} · total Q{total(checkout) / 100:.2f}")
    revisar_firma(checkout, perfil)

    paso(5, "Elijo la entrega que cumple el plazo y el presupuesto")
    opcion, notas = mejor_opcion(checkout, eleccion)
    print("\n".join(notas))
    if opcion is None:
        http.post(f"{endpoint}/checkout-sessions/{checkout['id']}/cancel", json={})
        alto("Ninguna opción cumple el encargo. Cancelé la sesión; no se compró nada.")
    grupo = checkout["fulfillment"]["methods"][0]["groups"][0]
    if opcion["id"] != grupo["selected_option_id"]:
        cambio = {**pedido, "fulfillment": {"methods": [{"id": "envio", "line_item_ids": grupo["line_item_ids"],
                  "groups": [{"id": grupo["id"], "selected_option_id": opcion["id"]}]}]}}
        checkout = http.put(f"{endpoint}/checkout-sessions/{checkout['id']}", json=cambio).json()
        print(f"  Actualizo la sesión: {opcion['title']} · total Q{total(checkout) / 100:.2f}")
        revisar_firma(checkout, perfil)
    else:
        print(f"  Me quedo con {opcion['title']}.")

    paso(6, "Me detengo antes de pagar: la compra la apruebas tú")
    if checkout["status"] != "ready_for_complete":
        alto(f"La sesión quedó en {checkout['status']}: {checkout.get('messages')}")
    for linea in checkout["line_items"]:
        print(f"  {linea['quantity']} × {linea['item']['title']}")
    print(f"  {opcion['title']}: {opcion['description']['plain']}")
    print(f"  Total: Q{total(checkout) / 100:.2f}, pago contra entrega")
    print(f"\n  Aprueba aquí: {checkout['continue_url']}")
    print(f"\nLlamadas a Gemini: {LLAMADAS_GEMINI}")
    print("Esperando tu decisión… (Ctrl+C para salir)")
    inicio = time.monotonic()
    while time.monotonic() - inicio < ESPERA_MAXIMA:
        time.sleep(3)
        actual = http.get(f"{endpoint}/checkout-sessions/{checkout['id']}").json()
        if actual.get("status") == "completed":
            revisar_firma(actual, perfil)
            print(f"✓ Aprobaste la compra: {actual['order']['label']} ({actual['order']['id']}).")
            return
        if actual.get("status") == "canceled":
            print("✗ Rechazaste la compra. No se hizo ningún pedido.")
            return
    print("Se acabó el tiempo de espera. La sesión sigue abierta en la tienda.")


if __name__ == "__main__":
    main()
