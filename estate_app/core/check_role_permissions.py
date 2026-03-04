
from fastapi import Depends,  HTTPException


from models.models import User
from models.enums import UserRole as Role
from core.get_current_user import get_current_user


def require_verified_user(user: User = Depends(get_current_user)):
    if not user.is_verified:
        raise HTTPException(
            status_code=403, detail="Please verify your email to access this feature"
        )
    return user


def require_admin_user(user: User = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=400, detail="Not Allowed"
        )
    return user
def require_user(user: User = Depends(get_current_user)):
    if user.role != Role.USER:
        raise HTTPException(
            status_code=400, detail="Not Allowed"
        )
    return user


def require_user_and_admin_user(
    user: User = Depends(get_current_user),
):
    if user.role not in {Role.ADMIN, Role.USER}:
        raise HTTPException(
            status_code=400, detail="Not Allowed"
        )
    return user
