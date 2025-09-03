# app/controllers/jwks_controller.py
from __future__ import annotations
from base64 import urlsafe_b64encode
from typing import Dict, Any
from pathlib import Path

from fastapi import APIRouter
from app.config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

import jwt
from jwt import InvalidTokenError


router = APIRouter(prefix="/.well-known", tags=["JWKS"])

def _b64u(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _load_public_numbers() -> Dict[str, Any]:
    # lê a chave pública PEM (arquivo)
    pub_path = Path(getattr(settings, "PUBLIC_KEY_PATH", "app/certs/jwt-public.pem"))
    pub = serialization.load_pem_public_key(pub_path.read_bytes(), backend=default_backend())
    if not isinstance(pub, rsa.RSAPublicKey):
        raise ValueError("JWKS requer RSA public key")
    numbers = pub.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    return {"n": _b64u(n), "e": _b64u(e)}

@router.get("/jwks.json")
def jwks():
    nums = _load_public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": settings.JWT_KID,
        "alg": "RS256",
        "use": "sig",
        "n": nums["n"],
        "e": nums["e"],
    }
    return {"keys": [jwk]}

__all__ = ["router"]
