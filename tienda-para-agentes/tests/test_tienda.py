"""La tienda terminada: páginas, datos estructurados, feed, perfil UCP, checkout y AP2."""

from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET

import pytest

import ap2
import ucp
from auditar import parse_html

G = "{http://base.google.com/ns/1.0}"
PEDIDO = {"line_items": [{"item": {"id": "hue-250-grueso"}, "quantity": 1}]}


def llaves(cliente):
    return cliente.get("/.well-known/ucp").json()["keys"]


def crear(cliente, cuerpo=PEDIDO):
    r = cliente.post("/ucp/v1/checkout-sessions", json=cuerpo)
    return r, r.json()


# --- Páginas y datos estructurados ------------------------------------------------------

def test_portada_se_lee_sin_javascript(cliente):
    pagina = parse_html(cliente.get("/").text, "http://testserver")
    assert "Huehuetenango Altura" in pagina["text"]
    assert len(pagina["text"]) > 80


def test_jsonld_del_producto(cliente):
    pagina = parse_html(cliente.get("/cafe/huehuetenango-altura").text, "http://testserver")
    grupo = pagina["jsonld"][0]
    assert grupo["@type"] == "ProductGroup" and grupo["variesBy"] == ["https://schema.org/size"]
    variantes = {v["sku"]: v for v in grupo["hasVariant"]}
    assert len(variantes) == 4
    oferta = variantes["hue-250-grueso"]["offers"]
    assert (oferta["price"], oferta["priceCurrency"]) == ("78.00", "GTQ")
    assert oferta["availability"] == "https://schema.org/InStock"
    assert variantes["hue-454-grano"]["offers"]["availability"] == "https://schema.org/OutOfStock"
    tiempo = oferta["shippingDetails"]["deliveryTime"]
    assert tiempo["handlingTime"]["maxValue"] == 1 and tiempo["transitTime"]["maxValue"] == 2


def test_feed_y_sitemap(cliente):
    feed = ET.fromstring(cliente.get("/feed.xml").text)
    items = list(feed.iter("item"))
    assert len(items) == 16
    primero = items[0]
    assert primero.find(f"{G}price").text == "78.00 GTQ"
    assert primero.find(f"{G}shipping/{G}max_transit_time").text == "2"
    locs = [e.text for e in ET.fromstring(cliente.get("/sitemap.xml").text).iter() if e.tag.endswith("loc")]
    assert locs[0].endswith("/cafe/huehuetenango-altura")


def test_pedido_de_una_persona(cliente):
    r = cliente.post("/pedidos", data={"sku": "ant-250-medio", "cantidad": "2", "nombre": "Ana"})
    assert r.status_code == 200 and "Recibimos tu pedido" in r.text
    assert cliente.post("/pedidos", data={"sku": "aca-250-grueso", "cantidad": "1"}).status_code == 400


# --- Perfil UCP ---------------------------------------------------------------------------

def test_perfil_ucp(cliente):
    r = cliente.get("/.well-known/ucp")
    assert "public" in r.headers["cache-control"] and "max-age=60" in r.headers["cache-control"]
    perfil = r.json()
    assert perfil["ucp"]["version"] == "2026-08-25"
    servicio = perfil["ucp"]["services"]["dev.ucp.shopping"][0]
    assert servicio["transport"] == "rest" and servicio["endpoint"].endswith("/ucp/v1")
    assert set(perfil["ucp"]["capabilities"]) == {
        "dev.ucp.shopping.checkout", "dev.ucp.shopping.fulfillment", "dev.ucp.common.payment.ap2_mandate"}
    assert perfil["ucp"]["payment_handlers"] == {}
    assert perfil["keys"][0]["kty"] == "EC" and perfil["keys"][0]["alg"] == "ES256"


# --- Checkout -------------------------------------------------------------------------------

def test_crear_checkout(cliente):
    r, chk = crear(cliente)
    assert r.status_code == 201
    assert chk["id"].startswith("chk_") and chk["status"] == "ready_for_complete"
    assert chk["currency"] == "GTQ"
    assert [t["amount"] for t in chk["totals"]] == [7800, 2000, 9800]
    assert chk["continue_url"].endswith(f"/aprobar/{chk['id']}")
    assert chk["ucp"]["payment_handlers"] == {}
    grupo = chk["fulfillment"]["methods"][0]["groups"][0]
    assert grupo["selected_option_id"] == "estandar" and [o["id"] for o in grupo["options"]] == ["estandar", "expres"]
    assert ap2.verificar_firma(chk, llaves(cliente))
    assert cliente.get(f"/ucp/v1/checkout-sessions/{chk['id']}").json() == chk


def test_firma_detecta_cambios(cliente):
    _, chk = crear(cliente)
    alterado = json.loads(json.dumps(chk))
    alterado["totals"][-1]["amount"] = 100
    assert not ap2.verificar_firma(alterado, llaves(cliente))


def test_sin_ucp_agent_responde_400(cliente):
    r = cliente.post("/ucp/v1/checkout-sessions", json=PEDIDO, headers={"UCP-Agent": ""})
    assert r.status_code == 400 and r.json()["code"] == "invalid_profile_url"


@pytest.mark.parametrize("sku,codigo", [("aca-250-grueso", "out_of_stock"), ("no-existe", "item_unavailable")])
def test_errores_de_negocio(cliente, sku, codigo):
    r, cuerpo = crear(cliente, {"line_items": [{"item": {"id": sku}, "quantity": 1}]})
    assert r.status_code == 200 and cuerpo["ucp"]["status"] == "error"
    assert cuerpo["messages"][0]["code"] == codigo


def test_actualizar_a_expres(cliente):
    _, chk = crear(cliente)
    cambio = {**PEDIDO, "fulfillment": {"methods": [{"id": "envio", "line_item_ids": ["li_1"],
                                                      "groups": [{"id": "paquete_1", "selected_option_id": "expres"}]}]}}
    nuevo = cliente.put(f"/ucp/v1/checkout-sessions/{chk['id']}", json=cambio).json()
    assert nuevo["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"] == "expres"
    assert nuevo["totals"][-1]["amount"] == 11300
    assert ap2.verificar_firma(nuevo, llaves(cliente))


def test_completar_sin_mandato_pide_a_la_persona(cliente):
    _, chk = crear(cliente)
    r = cliente.post(f"/ucp/v1/checkout-sessions/{chk['id']}/complete", json={"payment": {}})
    cuerpo = r.json()
    assert cuerpo["status"] == "requires_escalation"
    assert cuerpo["messages"][0]["code"] == "mandate_required"
    assert cuerpo["messages"][0]["severity"] == "requires_buyer_review"
    assert cuerpo["continue_url"].endswith(chk["id"])


def test_la_persona_aprueba(cliente):
    _, chk = crear(cliente)
    pagina = cliente.get(f"/aprobar/{chk['id']}")
    assert "¿Apruebas este pedido?" in pagina.text and "Q98.00" in pagina.text
    r = cliente.post(f"/aprobar/{chk['id']}", data={"decision": "aprobar"}, follow_redirects=False)
    assert r.status_code == 303
    cerrado = cliente.get(f"/ucp/v1/checkout-sessions/{chk['id']}").json()
    assert cerrado["status"] == "completed" and cerrado["order"]["id"].startswith("ord_")
    assert "continue_url" not in cerrado
    assert ap2.verificar_firma(cerrado, llaves(cliente))
    assert "confirmado" in cliente.get(f"/aprobar/{chk['id']}").text
    assert cliente.get(f"/pedidos/{cerrado['order']['id']}").status_code == 200
    assert cliente.post(f"/aprobar/{chk['id']}", data={"decision": "aprobar"}).status_code == 409


def test_la_persona_rechaza(cliente):
    _, chk = crear(cliente)
    cliente.post(f"/aprobar/{chk['id']}", data={"decision": "rechazar"})
    assert cliente.get(f"/ucp/v1/checkout-sessions/{chk['id']}").json()["status"] == "canceled"
    assert "Compra rechazada" in cliente.get(f"/aprobar/{chk['id']}").text


# --- AP2: completar por API con un mandato de una plataforma de confianza -----------------------

from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402

PLATAFORMA = ec.generate_private_key(ec.SECP256R1())
JWK_PLATAFORMA = ap2._jwk_de(PLATAFORMA.public_key())


def mandato(checkout: dict, aud: str = "http://testserver", exp: int | None = None, llave=PLATAFORMA) -> str:
    """Un SD-JWT de mandato de checkout como lo firmaría una plataforma (modelo de proveedor de confianza)."""
    jwt = ap2.checkout_jwt(checkout)
    d_jwt = ap2.b64url(json.dumps(["sal1", "checkout_jwt", jwt]).encode())
    cuerpo = {"vct": ap2.VCT_MANDATO, "checkout_hash": ap2.sha256_b64url(jwt), "_sd": [ap2.sha256_b64url(d_jwt)]}
    d_mandato = ap2.b64url(json.dumps(["sal2", cuerpo]).encode())
    claims = {"iss": "https://plataforma.example", "aud": aud, "iat": int(time.time()),
              "exp": exp or int(time.time()) + 300, "_sd_alg": "sha-256",
              "delegate_payload": [{"...": ap2.sha256_b64url(d_mandato)}]}
    emisor = ap2.firmar_jws(json.dumps(claims).encode(), llave, JWK_PLATAFORMA["kid"], typ="dc+sd-jwt")
    return f"{emisor}~{d_mandato}~{d_jwt}~"


@pytest.fixture()
def plataforma_confiable(monkeypatch):
    monkeypatch.setattr(ap2, "llaves_de_plataforma", lambda _: ([JWK_PLATAFORMA], None))


def completar(cliente, chk, m):
    return cliente.post(f"/ucp/v1/checkout-sessions/{chk['id']}/complete",
                        json={"payment": {}, "ap2": {"checkout_mandate": m}}).json()


def test_mandato_valido_completa(cliente, plataforma_confiable):
    _, chk = crear(cliente)
    assert completar(cliente, chk, mandato(chk))["status"] == "completed"


def test_mandato_de_otro_checkout(cliente, plataforma_confiable):
    _, chk = crear(cliente)
    _, otro = crear(cliente)
    r = completar(cliente, chk, mandato(otro))
    assert r["status"] == "ready_for_complete" and r["messages"][0]["code"] == "mandate_scope_mismatch"


def test_mandato_vencido_o_mal_firmado(cliente, plataforma_confiable):
    _, chk = crear(cliente)
    assert completar(cliente, chk, mandato(chk, exp=int(time.time()) - 5))["messages"][0]["code"] == "mandate_expired"
    intruso = ec.generate_private_key(ec.SECP256R1())
    assert completar(cliente, chk, mandato(chk, llave=intruso))["messages"][0]["code"] == "mandate_invalid_signature"
    assert completar(cliente, chk, mandato(chk, aud="https://otra.example"))["messages"][0]["code"] == "mandate_scope_mismatch"


def test_sin_plataformas_confiables_no_hay_completado_por_api(cliente, monkeypatch):
    monkeypatch.delenv("PLATAFORMAS_CONFIABLES", raising=False)
    _, chk = crear(cliente)
    r = completar(cliente, chk, mandato(chk))
    assert r["status"] == "ready_for_complete" and r["messages"][0]["code"] == "agent_missing_key"


def test_entrega_expres_no_cae_en_domingo():
    from datetime import date

    from catalogo import ventana_entrega

    sabado = date(2026, 10, 17)
    assert ventana_entrega("expres", sabado)[0] == date(2026, 10, 19)
    assert ventana_entrega("estandar", date(2026, 10, 12)) == (date(2026, 10, 14), date(2026, 10, 15))
    assert ucp.UCP_VERSION == "2026-08-25"
