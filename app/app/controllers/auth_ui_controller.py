# app/controllers/auth_ui_controller.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal, Any, Dict

from fastapi import APIRouter, Depends, Request, Response, Body, status, Cookie, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr, Field

from app.core.logging_config import get_logger
from app.services.auth_wiring import build_auth_service_from_settings
from app.services.auth_service import AuthError

import jwt
from jwt import InvalidTokenError
from app.config import settings

logger = get_logger("assistente")

# Endpoints públicos de autenticação da UI (versionados)
router = APIRouter(prefix="/auth", tags=["Auth"])

# -----------------------------------------------------------------------------
# Schemas (Pydantic) — fiéis aos contratos
# -----------------------------------------------------------------------------
class Preferences(BaseModel):
    themePreferred: Optional[Literal["vscode", "light", "dark"]] = None
    moduleOrder: Optional[List[str]] = None
    iconOrder: Optional[List[str]] = None

class User(BaseModel):
    id: str
    login: str
    nome: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: bool
    status: Literal["active", "disabled"]
    senhaHash: Optional[str] = Field(default=None, exclude=True)
    senhaUpdatedAt: Optional[str] = Field(default=None, exclude=True)
    lastLoginAt: Optional[str] = None
    lastLoginIp: Optional[str] = None
    createdAt: str
    updatedAt: str
    ui: Optional[Preferences] = None
    modules: Optional[List[str]] = None


class LoginRequest(BaseModel):
    login: str
    senha: constr(min_length=4)


class LoginResponse(BaseModel):
    accessToken: str
    accessTokenExpiresIn: int
    refreshToken: Optional[str] = None
    refreshTokenExpiresIn: Optional[int] = None
    user: User


class RefreshResponse(BaseModel):
    accessToken: str
    accessTokenExpiresIn: int
    refreshToken: Optional[str] = None
    refreshTokenExpiresIn: Optional[int] = None


class LogoutResponse(BaseModel):
    ok: bool


class RequestPasswordResetRequest(BaseModel):
    login: str


class RequestPasswordResetResponse(BaseModel):
    message: str = "Token de reset enviado por email/SMS"


class ConfirmPasswordResetRequest(BaseModel):
    token: str
    newPassword: constr(min_length=4)


class ConfirmPasswordResetResponse(BaseModel):
    message: str = "Senha alterada com sucesso"


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    traceId: Optional[str] = None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _error_response(status_code: int, *, error: str, message: str, details: Optional[Dict[str, Any]] = None,
                    trace_id: Optional[str] = None) -> JSONResponse:
    payload = ErrorResponse(error=error, message=message, details=details, traceId=trace_id).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _client_hints(req: Request) -> tuple[Optional[str], Optional[str]]:
    # Melhor esforço para capturar UA e IP (ajuste conforme proxy)
    ua = req.headers.get("User-Agent")
    fwd = req.headers.get("X-Forwarded-For")
    ip = (fwd.split(",")[0].strip() if fwd else req.client.host if req.client else None)
    return ua, ip


def _pick_refresh_from_headers(req: Request) -> Optional[str]:
    # Política padrão: header X-Refresh-Token (troque para cookie/body se preferir)
    return req.headers.get("X-Refresh-Token")

def _pick_bearer_from_auth(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

def build_user_response(u) -> User:
    """Monta o objeto User (Pydantic) para resposta, sem campos sensíveis."""
    return User(
        id=u.id,
        login=u.login,
        nome=u.nome,
        email=u.email,
        whatsapp=u.whatsapp,
        isAdmin=u.isAdmin,
        status=u.status,
        lastLoginAt=u.lastLoginAt,
        lastLoginIp=u.lastLoginIp,
        createdAt=u.createdAt,
        updatedAt=u.updatedAt,
        ui=u.ui,
        modules=u.modules,
    )


# -----------------------------------------------------------------------------
# Wiring do serviço
# -----------------------------------------------------------------------------
auth_service = build_auth_service_from_settings()

# -----------------------------------------------------------------------------
# Endpoints (contratos 1:1)
# -----------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def login(
    req: Request,
    response: Response,
    body: LoginRequest = Body(...),
) -> LoginResponse | JSONResponse:
    logger.info("auth.login.start", extra={"login": body.login})
    try:
        ua, ip = _client_hints(req)

        bundle = await auth_service.login(
            login=body.login,
            senha=body.senha,
            user_agent=ua,
            client_ip=ip,
        )

        user = build_user_response(bundle.user)

        # seta cookie HttpOnly + Secure com o refresh (browser-friendly)
        if bundle.refresh_token:
            response.set_cookie(
                key="refreshToken",
                value=bundle.refresh_token,
                httponly=True,
                secure=True,
                samesite="strict",
                path="/v1/auth",
                max_age=bundle.refresh_expires_in,
                domain=settings.COOKIE_DOMAIN,
            )

        logger.info("auth.login.ok", extra={"login": body.login})
        return LoginResponse(
            accessToken=bundle.access_token,
            accessTokenExpiresIn=bundle.access_expires_in,
            refreshToken=bundle.refresh_token,
            refreshTokenExpiresIn=bundle.refresh_expires_in,
            user=user,
        )

    except AuthError as e:
        logger.info("auth.login.fail", extra={"login": body.login, "code": e.code})
        status_map = {
            "ERR_USER_NOT_FOUND": 401,
            "ERR_INVALID_SENHA": 401,
            "ERR_USER_DISABLED": 403,
        }
        sc = status_map.get(e.code, 400)
        return _error_response(sc, error=e.code, message=e.message)
    except Exception:
        logger.exception("auth.login.error")
        return _error_response(500, error="ERR_INTERNAL", message="Erro interno")

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def refresh(req: Request, response: Response, refresh_token: Optional[str] = Cookie(None, alias="refreshToken")) -> RefreshResponse | JSONResponse:
    logger.info("auth.refresh.start")
    try:
        ua, ip = _client_hints(req)

        # Fallback: se não veio cookie, tenta o header legado
        raw_refresh = refresh_token or req.headers.get("X-Refresh-Token")

        bundle = await auth_service.refresh_token(
            raw_refresh_token=raw_refresh, user_agent=ua, client_ip=ip
        )
        logger.info("auth.refresh.ok")

        # Renova o cookie com o NOVO refresh (HttpOnly + Secure)
        if bundle.refresh_token:
            response.set_cookie(
                key="refreshToken",
                value=bundle.refresh_token,
                httponly=True,
                secure=True,
                samesite="strict",
                path="/v1/auth",
                max_age=bundle.refresh_expires_in,
                domain=settings.COOKIE_DOMAIN,
            )

        # retorna no formato do schema
        return RefreshResponse(
            accessToken=bundle.access_token,
            accessTokenExpiresIn=bundle.access_expires_in,
            refreshToken=bundle.refresh_token,
            refreshTokenExpiresIn=bundle.refresh_expires_in,
        )

    except AuthError as e:
        logger.info("auth.refresh.fail", extra={"code": e.code})
        status_map = {
            "ERR_REFRESH_MISSING": 401,
            "ERR_REFRESH_INVALID": 401,
            "ERR_REFRESH_REVOKED": 401,
            "ERR_REFRESH_EXPIRED": 401,
            "ERR_USER_DISABLED": 403,
            "ERR_USER_NOT_FOUND": 401,
        }
        sc = status_map.get(e.code, 400)
        return _error_response(sc, error=e.code, message=e.message)
    except Exception:
        logger.exception("auth.refresh.error")
        return _error_response(500, error="ERR_INTERNAL", message="Erro interno")

@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def logout(
    req: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="refreshToken"),
) -> LogoutResponse | JSONResponse:
    logger.info("auth.logout.start")
    try:
        # Fallback: se não veio cookie, tenta header legado
        raw_refresh = refresh_token or req.headers.get("X-Refresh-Token")

        await auth_service.logout(raw_refresh_token=raw_refresh)
        logger.info("auth.logout.ok")

        # apaga o cookie (idempotente)
        response.delete_cookie(
            key="refreshToken",
            path="/v1/auth",
            domain=settings.COOKIE_DOMAIN
        )

        return LogoutResponse(ok=True)

    except Exception:
        logger.exception("auth.logout.error")
        return _error_response(500, error="ERR_INTERNAL", message="Erro interno")


@router.post(
    "/request-password-reset",
    response_model=RequestPasswordResetResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def request_password_reset(
    req: Request,
    body: RequestPasswordResetRequest,
) -> RequestPasswordResetResponse | JSONResponse:
    logger.info("auth.request_password_reset.start", extra={"login": body.login})
    try:
        ua, ip = _client_hints(req)

        reset_token = await auth_service.request_password_reset(
            login=body.login,
            user_agent=ua,
            client_ip=ip,
        )

        # TODO: Enviar token por email/SMS
        # Por enquanto, apenas logamos o token (em produção, NUNCA fazer isso!)
        logger.info("auth.request_password_reset.token_generated", extra={
            "login": body.login, 
            "token": reset_token  # REMOVER EM PRODUÇÃO!
        })

        logger.info("auth.request_password_reset.ok", extra={"login": body.login})
        return RequestPasswordResetResponse()

    except AuthError as e:
        logger.info("auth.request_password_reset.fail", extra={"login": body.login, "code": e.code})
        status_map = {
            "ERR_USER_NOT_FOUND": 401,
            "ERR_USER_DISABLED": 403,
        }
        sc = status_map.get(e.code, 400)
        return _error_response(sc, error=e.code, message=e.message)
    except Exception:
        logger.exception("auth.request_password_reset.error")
        return _error_response(500, error="ERR_INTERNAL", message="Erro interno")


@router.post(
    "/confirm-password-reset",
    response_model=ConfirmPasswordResetResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def confirm_password_reset(
    req: Request,
    body: ConfirmPasswordResetRequest,
) -> ConfirmPasswordResetResponse | JSONResponse:
    logger.info("auth.confirm_password_reset.start")
    try:
        ua, ip = _client_hints(req)

        await auth_service.confirm_password_reset(
            reset_token=body.token,
            new_password=body.newPassword,
            user_agent=ua,
            client_ip=ip,
        )

        logger.info("auth.confirm_password_reset.ok")
        return ConfirmPasswordResetResponse()

    except AuthError as e:
        logger.info("auth.confirm_password_reset.fail", extra={"code": e.code})
        status_map = {
            "ERR_RESET_TOKEN_MISSING": 400,
            "ERR_RESET_TOKEN_INVALID": 401,
            "ERR_RESET_TOKEN_USED": 401,
            "ERR_RESET_TOKEN_EXPIRED": 401,
            "ERR_USER_NOT_FOUND": 401,
            "ERR_USER_DISABLED": 403,
        }
        sc = status_map.get(e.code, 400)
        return _error_response(sc, error=e.code, message=e.message)
    except Exception:
        logger.exception("auth.confirm_password_reset.error")
        return _error_response(500, error="ERR_INTERNAL", message="Erro interno")


__all__ = ["router"]
