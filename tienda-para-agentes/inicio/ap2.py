"""Firmas de la extensión AP2 Mandates de UCP (versión 2026-08-25), ya escritas.

- La tienda firma cada checkout: JWS ES256 con contenido separado (RFC 7515,
  apéndice F) sobre JCS (RFC 8785) del checkout sin el campo "ap2".
- Quien recibe el checkout (el agente) verifica esa firma con la llave pública
  que la tienda publica en `keys[]` de /.well-known/ucp.
- Para completar por API, la tienda exige un mandato de checkout (SD-JWT,
  vct "mandate.checkout.1") firmado por una plataforma de confianza en nombre
  de la persona. Sin plataformas de confianza configuradas, nadie completa por
  API: la persona aprueba en la página de la tienda (continue_url).

Especificación: https://ucp.dev/2026-08-25/specification/payment/extensions/ap2-mandates/
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

ARCHIVO_LLAVE = Path(os.environ.get("LLAVE_TIENDA", ".llave_tienda.pem"))
VCT_MANDATO = "mandate.checkout.1"


# --- Codificación ---------------------------------------------------------------------

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def de_b64url(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def jcs(valor: Any) -> bytes:
    """JSON canónico (RFC 8785) para nuestros datos: llaves ordenadas, sin espacios,
    montos siempre enteros (centavos), así que no hay decimales que formatear."""
    return json.dumps(valor, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_b64url(texto: str) -> str:
    return b64url(hashlib.sha256(texto.encode("ascii")).digest())


# --- Llave de la tienda ---------------------------------------------------------------

_llave: ec.EllipticCurvePrivateKey | None = None


def llave_tienda() -> ec.EllipticCurvePrivateKey:
    """Lee la llave P-256 de la tienda o la crea la primera vez (archivo privado)."""
    global _llave
    if _llave is None:
        if ARCHIVO_LLAVE.exists():
            _llave = serialization.load_pem_private_key(ARCHIVO_LLAVE.read_bytes(), password=None)
        else:
            _llave = ec.generate_private_key(ec.SECP256R1())
            pem = _llave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption())
            ARCHIVO_LLAVE.write_bytes(pem)
            ARCHIVO_LLAVE.chmod(0o600)
    return _llave


def _jwk_de(publica: ec.EllipticCurvePublicKey) -> dict[str, str]:
    numeros = publica.public_numbers()
    jwk = {"crv": "P-256", "kty": "EC",
           "x": b64url(numeros.x.to_bytes(32, "big")), "y": b64url(numeros.y.to_bytes(32, "big"))}
    kid = b64url(hashlib.sha256(jcs(jwk)).digest())  # huella JWK (RFC 7638)
    return {**jwk, "kid": kid, "use": "sig", "alg": "ES256"}


def jwk_publica() -> dict[str, str]:
    return _jwk_de(llave_tienda().public_key())


def _publica_de(jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
    x = int.from_bytes(de_b64url(jwk["x"]), "big")
    y = int.from_bytes(de_b64url(jwk["y"]), "big")
    return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()


# --- JWS ES256 ------------------------------------------------------------------------

def _firmar_es256(entrada: bytes, llave: ec.EllipticCurvePrivateKey) -> str:
    r, s = decode_dss_signature(llave.sign(entrada, ec.ECDSA(hashes.SHA256())))
    return b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def _verificar_es256(entrada: bytes, firma_b64: str, jwk: dict[str, Any]) -> bool:
    firma = de_b64url(firma_b64)
    if len(firma) != 64:
        return False
    der = encode_dss_signature(int.from_bytes(firma[:32], "big"), int.from_bytes(firma[32:], "big"))
    try:
        _publica_de(jwk).verify(der, entrada, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError):
        return False


def firmar_jws(contenido: bytes, llave: ec.EllipticCurvePrivateKey, kid: str, typ: str | None = None) -> str:
    """JWS compacto: encabezado.contenido.firma."""
    encabezado = {"alg": "ES256", "kid": kid, **({"typ": typ} if typ else {})}
    h = b64url(json.dumps(encabezado, separators=(",", ":")).encode())
    p = b64url(contenido)
    return f"{h}.{p}.{_firmar_es256(f'{h}.{p}'.encode('ascii'), llave)}"


# --- Firma del checkout (lo que hace la tienda) ---------------------------------------

def sin_ap2(checkout: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in checkout.items() if k != "ap2"}


def firmar(checkout: dict[str, Any]) -> dict[str, Any]:
    """Agrega ap2.merchant_authorization: JWS separado `encabezado..firma`."""
    jws = firmar_jws(jcs(sin_ap2(checkout)), llave_tienda(), jwk_publica()["kid"])
    encabezado, _, firma = jws.split(".")
    return {**checkout, "ap2": {"merchant_authorization": f"{encabezado}..{firma}"}}


def verificar_firma(checkout: dict[str, Any], llaves: list[dict[str, Any]]) -> bool:
    """La verificación que hace el agente antes de mostrarle el checkout a la persona."""
    autorizacion = (checkout.get("ap2") or {}).get("merchant_authorization")
    if not isinstance(autorizacion, str) or autorizacion.count(".") != 2:
        return False
    h, vacio, firma = autorizacion.split(".")
    try:
        encabezado = json.loads(de_b64url(h))
    except ValueError:
        return False
    jwk = next((k for k in llaves if k.get("kid") == encabezado.get("kid")), None)
    if vacio or encabezado.get("alg") != "ES256" or jwk is None:
        return False
    entrada = f"{h}.{b64url(jcs(sin_ap2(checkout)))}".encode("ascii")
    return _verificar_es256(entrada, firma, jwk)


def checkout_jwt(checkout: dict[str, Any]) -> str:
    """El checkout firmado con su contenido adjunto: lo que el mandato incluye."""
    h, _, firma = checkout["ap2"]["merchant_authorization"].split(".")
    return f"{h}.{b64url(jcs(sin_ap2(checkout)))}.{firma}"


# --- Mandato de checkout (lo que exige la tienda para completar por API) --------------

def plataformas_confiables() -> list[str]:
    return [p.strip() for p in os.environ.get("PLATAFORMAS_CONFIABLES", "").split(",") if p.strip()]


def llaves_de_plataforma(ucp_agent: str | None) -> tuple[list[dict[str, Any]], str | None]:
    """Llaves públicas de la plataforma que firma el mandato (solo si es de confianza)."""
    m = re.search(r'profile="([^"]+)"', ucp_agent or "")
    if not m:
        return [], "Falta el encabezado UCP-Agent con el perfil de la plataforma."
    if m.group(1) not in plataformas_confiables():
        return [], "Esta tienda no acepta mandatos de esa plataforma."
    try:
        perfil = httpx.get(m.group(1), timeout=10, follow_redirects=False).json()
    except (httpx.HTTPError, ValueError):
        return [], "No se pudo leer el perfil de la plataforma."
    return [k for k in perfil.get("keys", []) if isinstance(k, dict)], None


def verificar_mandato(mandato: Any, checkout: dict[str, Any], llaves_plataforma: list[dict[str, Any]],
                      host_tienda: str) -> tuple[bool, str, str]:
    """Devuelve (ok, código de error UCP, motivo)."""
    if not isinstance(mandato, str) or not mandato:
        return False, "mandate_required", "Falta ap2.checkout_mandate."
    emisor, *resto = mandato.split("~")
    divulgaciones = {sha256_b64url(d): d for d in resto if d}
    try:
        h, p, firma = emisor.split(".")
        encabezado = json.loads(de_b64url(h))
        jwk = next((k for k in llaves_plataforma if k.get("kid") == encabezado.get("kid")), None)
        if jwk is None:
            return False, "agent_missing_key", "El mandato usa una llave que la plataforma no publica."
        if encabezado.get("alg") != "ES256" or not _verificar_es256(f"{h}.{p}".encode("ascii"), firma, jwk):
            return False, "mandate_invalid_signature", "La firma del mandato no es válida."
        claims = json.loads(de_b64url(p))
        if not isinstance(claims.get("exp"), int) or claims["exp"] < time.time():
            return False, "mandate_expired", "El mandato expiró."
        if urlparse(str(claims.get("aud", ""))).netloc != host_tienda:
            return False, "mandate_scope_mismatch", "El mandato no está dirigido a esta tienda."
        resumen = (claims.get("delegate_payload") or [{}])[0].get("...")
        _, cuerpo = json.loads(de_b64url(divulgaciones[resumen]))
        if cuerpo.get("vct") != VCT_MANDATO:
            return False, "mandate_invalid_signature", "Tipo de mandato incorrecto."
        resumen_jwt = next(d for d in cuerpo.get("_sd", []) if d in divulgaciones)
        _, nombre, jwt = json.loads(de_b64url(divulgaciones[resumen_jwt]))
        if nombre != "checkout_jwt" or sha256_b64url(jwt) != cuerpo.get("checkout_hash"):
            return False, "mandate_scope_mismatch", "checkout_hash no coincide con el checkout firmado."
    except (ValueError, KeyError, IndexError, StopIteration, TypeError, AttributeError):
        return False, "mandate_invalid_signature", "El mandato no es un SD-JWT legible."
    if jwt != checkout_jwt(checkout):
        return False, "mandate_scope_mismatch", "El mandato aprueba otros términos o fue firmado por otra tienda."
    return True, "", ""
