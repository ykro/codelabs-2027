"""UCP en la tienda: perfil de comercio y sesiones de checkout (REST).

Sigue la versión 2026-08-25 de la especificación (https://ucp.dev/2026-08-25/).
Montos en centavos de quetzal. Las sesiones viven en memoria: al reiniciar el
servidor se pierden, como un carrito sin guardar.
"""

from __future__ import annotations

import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import ap2
from catalogo import ENVIOS, momento, rango_fechas, titulo_variante, variante, ventana_entrega

UCP_VERSION = "2026-08-25"
SPEC = f"https://ucp.dev/{UCP_VERSION}"

SESIONES: dict[str, dict[str, Any]] = {}
PEDIDOS: dict[str, dict[str, Any]] = {}
_candado = threading.Lock()


def base_publica(base: str) -> str:
    """URL que abre la persona (en Cloud Shell, la de la vista previa web)."""
    return os.environ.get("URL_PUBLICA", base).rstrip("/")


# --- Paso 7: perfil de comercio (/.well-known/ucp) ------------------------------------

# TODO paso 7 (perfil): reemplaza esta función por el perfil de comercio.
def perfil(base: str) -> dict[str, Any]:
    return {}


# --- Paso 7: capacidades y sesión de checkout -----------------------------------------

# TODO paso 7 (capacidades): reemplaza esta función por las capacidades de la tienda.
def capacidades() -> dict[str, list[dict[str, Any]]]:
    return {}


# TODO paso 7 (armar_checkout): reemplaza esta función por la sesión de checkout.
def armar_checkout(id_sesion: str, pedidas: Any, envio: str, base: str) -> tuple[dict | None, dict | None]:
    raise NotImplementedError("Completa el paso 7")


# --- Paso 8: firmas AP2 ---------------------------------------------------------------

# TODO paso 8 (firmas_ap2): reemplaza estas tres funciones por las de AP2.
def capacidad_ap2() -> dict[str, list[dict[str, Any]]]:
    return {}


def llaves_publicas() -> list[dict[str, str]]:
    return []


def firmar(checkout: dict[str, Any]) -> dict[str, Any]:
    return checkout


# --- Piezas del checkout (ya escritas) ------------------------------------------------

def lineas_con_precio(pedidas: Any) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Valida line_items [{item: {id}, quantity}] y les pone precio y título de la tienda."""
    if not isinstance(pedidas, list) or not pedidas:
        return [], mensaje("invalid_input", "Incluye al menos un line_item con item.id y quantity.")
    lineas = []
    for n, pedida in enumerate(pedidas, start=1):
        sku = str(((pedida or {}).get("item") or {}).get("id", ""))
        cantidad = (pedida or {}).get("quantity", 1)
        p, v = variante(sku)
        if v is None:
            return [], mensaje("item_unavailable", f"No vendemos «{sku}».", f"$.line_items[{n - 1}]")
        if not v["disponible"]:
            return [], mensaje("out_of_stock", f"{titulo_variante(p, v)} está agotado.", f"$.line_items[{n - 1}]")
        if not isinstance(cantidad, int) or not 1 <= cantidad <= 10:
            return [], mensaje("invalid_input", "quantity debe ser un entero de 1 a 10.", f"$.line_items[{n - 1}]")
        subtotal = v["precio"] * cantidad
        lineas.append({
            "id": f"li_{n}",
            "item": {"id": sku, "title": titulo_variante(p, v), "price": v["precio"]},
            "quantity": cantidad,
            "totals": [{"type": "subtotal", "amount": subtotal}, {"type": "total", "amount": subtotal}],
        })
    return lineas, None


def opcion_envio(clave: str) -> dict[str, Any]:
    """Una opción de entrega con su costo y su ventana de fechas exacta."""
    desde, hasta = ventana_entrega(clave)
    return {
        "id": clave,
        "title": ENVIOS[clave]["titulo"],
        "description": {"plain": f"Llega {rango_fechas(desde, hasta)}. Entregamos de {ENVIOS[clave]['dias']}."},
        "earliest_fulfillment_time": momento(desde, 9),
        "latest_fulfillment_time": momento(hasta, 18),
        "totals": [{"type": "total", "amount": ENVIOS[clave]["precio"]}],
    }


def opcion_pedida(cuerpo: dict[str, Any], actual: str = "estandar") -> str:
    """Lee fulfillment.methods[].groups[].selected_option_id de la petición."""
    for metodo in ((cuerpo.get("fulfillment") or {}).get("methods") or []):
        for grupo in metodo.get("groups") or []:
            if grupo.get("selected_option_id") in ENVIOS:
                return grupo["selected_option_id"]
    return actual


def mensaje(codigo: str, texto: str, ruta: str | None = None, severidad: str = "recoverable") -> dict[str, Any]:
    m = {"type": "error", "code": codigo, "content": texto, "severity": severidad}
    return {**m, "path": ruta} if ruta else m


def meta_respuesta() -> dict[str, Any]:
    activas = {nombre: [{"version": UCP_VERSION}] for nombre in capacidades()}
    return {"version": UCP_VERSION, "capabilities": activas, "payment_handlers": {}}


def utc(mas: timedelta = timedelta()) -> str:
    """Fecha y hora RFC 3339 en UTC, como la usa UCP."""
    return (datetime.now(timezone.utc) + mas).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Completar: solo la persona (o un mandato AP2 válido) -----------------------------

def completar(id_sesion: str, base: str) -> dict[str, Any] | None:
    """Cierra la sesión y crea el pedido. Pago contra entrega: no se cobra nada aquí."""
    with _candado:
        sesion = SESIONES.get(id_sesion)
        if sesion is None or sesion["status"] not in {"ready_for_complete", "requires_escalation"}:
            return None
        if sesion["expires_at"] < utc():
            return None
        id_pedido = f"ord_{secrets.token_hex(6)}"
        cerrado = {k: v for k, v in sesion.items() if k not in {"continue_url", "messages", "ap2"}}
        cerrado["status"] = "completed"
        cerrado["order"] = {"id": id_pedido, "label": f"Pedido {id_pedido[-6:].upper()}",
                            "permalink_url": f"{base_publica(base)}/pedidos/{id_pedido}"}
        SESIONES[id_sesion] = firmar(cerrado)
        PEDIDOS[id_pedido] = {"id": id_pedido, "checkout": SESIONES[id_sesion], "creado": utc()}
        return SESIONES[id_sesion]


def cancelar(id_sesion: str) -> dict[str, Any] | None:
    with _candado:
        sesion = SESIONES.get(id_sesion)
        if sesion is None or sesion["status"] in {"completed", "canceled"}:
            return None
        cerrado = {k: v for k, v in sesion.items() if k not in {"continue_url", "messages", "ap2"}}
        cerrado["status"] = "canceled"
        SESIONES[id_sesion] = firmar(cerrado)
        return SESIONES[id_sesion]


# --- Rutas REST: {endpoint}/checkout-sessions -----------------------------------------

rutas = APIRouter(prefix="/ucp/v1")


def _base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _sin_agente(request: Request) -> JSONResponse | None:
    if 'profile="' not in request.headers.get("ucp-agent", ""):
        return JSONResponse({"code": "invalid_profile_url",
                             "content": 'Falta el encabezado UCP-Agent: profile="https://…"'}, status_code=400)
    return None


def _error(m: dict[str, Any], base: str, status: int = 200) -> JSONResponse:
    cuerpo = {"ucp": {"version": UCP_VERSION, "status": "error"}, "messages": [m], "continue_url": base_publica(base)}
    return JSONResponse(cuerpo, status_code=status)


def _no_encontrada(base: str) -> JSONResponse:
    return _error(mensaje("not_found", "No existe esa sesión de checkout.", severidad="unrecoverable"), base, 404)


@rutas.post("/checkout-sessions")
async def crear_sesion(request: Request):
    if (falla := _sin_agente(request)) is not None:
        return falla
    cuerpo = await request.json()
    id_sesion = f"chk_{secrets.token_hex(8)}"
    checkout, error = armar_checkout(id_sesion, cuerpo.get("line_items"), opcion_pedida(cuerpo), _base(request))
    if error:
        return _error(error, _base(request))
    SESIONES[id_sesion] = firmar(checkout)
    return JSONResponse(SESIONES[id_sesion], status_code=201)


@rutas.get("/checkout-sessions/{id_sesion}")
async def ver_sesion(id_sesion: str, request: Request):
    if (falla := _sin_agente(request)) is not None:
        return falla
    sesion = SESIONES.get(id_sesion)
    return JSONResponse(sesion) if sesion else _no_encontrada(_base(request))


@rutas.put("/checkout-sessions/{id_sesion}")
async def actualizar_sesion(id_sesion: str, request: Request):
    if (falla := _sin_agente(request)) is not None:
        return falla
    sesion = SESIONES.get(id_sesion)
    if sesion is None:
        return _no_encontrada(_base(request))
    if sesion["status"] not in {"ready_for_complete", "incomplete"}:
        return JSONResponse({**sesion, "messages": [mensaje("invalid_state", "Esta sesión ya no se puede cambiar.")]})
    cuerpo = await request.json()
    actual = sesion["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"]
    checkout, error = armar_checkout(id_sesion, cuerpo.get("line_items"), opcion_pedida(cuerpo, actual), _base(request))
    if error:
        return JSONResponse({**sesion, "messages": [error]})
    SESIONES[id_sesion] = firmar(checkout)
    return JSONResponse(SESIONES[id_sesion])


@rutas.post("/checkout-sessions/{id_sesion}/complete")
async def completar_sesion(id_sesion: str, request: Request):
    """Por API solo se completa con un mandato AP2 de una plataforma de confianza.
    Sin mandato, la sesión pasa a requires_escalation: la persona aprueba en continue_url."""
    if (falla := _sin_agente(request)) is not None:
        return falla
    base = _base(request)
    sesion = SESIONES.get(id_sesion)
    if sesion is None:
        return _no_encontrada(base)
    if sesion["status"] not in {"ready_for_complete", "requires_escalation"}:
        return JSONResponse({**sesion, "messages": [mensaje("invalid_state", "Esta sesión ya está cerrada.")]})
    cuerpo = await request.json()
    mandato = (cuerpo.get("ap2") or {}).get("checkout_mandate")
    if not mandato:
        escalada = {**ap2.sin_ap2(sesion), "status": "requires_escalation", "messages": [mensaje(
            "mandate_required", "La persona debe aprobar esta compra en continue_url.", severidad="requires_buyer_review")]}
        SESIONES[id_sesion] = firmar(escalada)
        return JSONResponse(SESIONES[id_sesion])
    llaves, problema = ap2.llaves_de_plataforma(request.headers.get("ucp-agent"))
    if problema:
        return JSONResponse({**sesion, "messages": [mensaje("agent_missing_key", problema)]})
    ok, codigo, motivo = ap2.verificar_mandato(mandato, sesion, llaves, request.url.netloc)
    if not ok:
        return JSONResponse({**sesion, "messages": [mensaje(codigo, motivo)]})
    return JSONResponse(completar(id_sesion, base))


@rutas.post("/checkout-sessions/{id_sesion}/cancel")
async def cancelar_sesion(id_sesion: str, request: Request):
    if (falla := _sin_agente(request)) is not None:
        return falla
    cancelada = cancelar(id_sesion)
    if cancelada is None:
        return _no_encontrada(_base(request)) if id_sesion not in SESIONES else JSONResponse(
            {**SESIONES[id_sesion], "messages": [mensaje("invalid_state", "Esta sesión ya está cerrada.")]})
    return JSONResponse(cancelada)
