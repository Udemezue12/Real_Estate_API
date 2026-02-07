from fastapi import Depends, HTTPException, WebSocket, Request
from models.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .get_db import get_db_async
from .validators import decode_ws_access_token, jwt_protect, passkey_jwt_protect


async def get_current_user_for_login(
    request: Request,
    db: AsyncSession = Depends(get_db_async),
):
    try:
        user_id = await jwt_protect(request)

        if not user_id:
            return None

    except Exception:
        return None

    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalars().first()

    return user


async def get_current_user(
    user_id: str = Depends(jwt_protect), db: AsyncSession = Depends(get_db_async)
):
    try:
        user_uuid = user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format in token")

    user = await db.execute(select(User).where(User.id == user_uuid))
    user_result = user.scalars().first()

    if not user_result:
        raise HTTPException(status_code=404, detail="Not Authenticated")

    return user_result


async def passkey_get_current_user(
    user_id: str = Depends(passkey_jwt_protect),
    db: AsyncSession = Depends(get_db_async),
) -> User:
    try:
        user_uuid = user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format in token")
    user = await db.execute(select(User).where(User.id == user_uuid))
    user_result = user.scalars().first()
    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")
    return user_result


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession,
):
    token = websocket.cookies.get("access_token")

    if not token:
        await websocket.close(code=4401)
        raise RuntimeError("Not authenticated")

    try:
        user_id = decode_ws_access_token(token)
    except ValueError:
        await websocket.close(code=4401)
        raise RuntimeError("Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        await websocket.close(code=4401)
        raise RuntimeError("User not found")

    return user
