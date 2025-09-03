# app/controllers/private_controller.py
from fastapi import APIRouter, Depends

from app.security.jwt_dependency import require_user, require_admin, CurrentUser

router = APIRouter(prefix="/v1/private", tags=["Private"])

@router.get("/ping")
async def private_ping(current: CurrentUser = Depends(require_user)):
    # current = {"sub": "...", "roles": [...], "sid": "..."}
    return {"ok": True, "userId": current["sub"], "roles": current["roles"]}


@router.get("/ping_admin")
async def admin_ping(current: CurrentUser = Depends(require_admin)):
    return {
        "ok": True,
        "adminId": current["sub"],
        "roles": current["roles"],
    }

__all__ = ["router"]

__all__ = ["router"]
