from fastapi import Depends, HTTPException, Request
from models.models import User

from .get_current_user import get_current_user_for_login as get_current_user


async def check_not_logged_in(
    current_user: User = Depends(get_current_user),
):
    if current_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Already logged in",
        )


async def check_logged_in(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in",
        )

    return current_user
