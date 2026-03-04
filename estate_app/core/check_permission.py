from fastapi import HTTPException
from models.enums import UserRole
from models.models import User


class CheckRolePermission:

    async def check_admin(self, current_user: User):
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Access Denied."
            )

    async def check_authenticated(self, current_user: User):
        if current_user.role not in {
            UserRole.ADMIN,
            UserRole.USER,
            UserRole.LANDLORD,
            UserRole.TENANT,
        }:
            raise HTTPException(
                status_code=403,
                detail="Access Denied."
            )

    async def check_login(self, current_user: User):
        if current_user.role in {
            UserRole.ADMIN,
            UserRole.USER,
            UserRole.LANDLORD,
            UserRole.TENANT,
        }:
            raise HTTPException(
                status_code=400,
                detail="Already Logged In."
            )

    async def check_role(self, role: UserRole):
        if role not in {
            UserRole.ADMIN,
            UserRole.USER,
            UserRole.LANDLORD,
            UserRole.TENANT,
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid Role."
            )