from fastapi import HTTPException
from models.enums import UserRole


class CheckRolePermission:
    async def check_landlord(self, current_user):
        if current_user.role.name != UserRole.LANDLORD:
            raise HTTPException(status_code=403, detail="Access Denied.")

    async def check_tenant(self, current_user):
        if current_user.role.name != UserRole.TENANT:
            raise HTTPException(status_code=403, detail="Access Denied.")

    async def check_lawyer(self, current_user):
        if current_user.role.name != UserRole.LAWYER:
            raise HTTPException(status_code=403, detail="Access Denied.")

    async def check_caretaker(self, current_user):
        if current_user.role.name != UserRole.CARETAKER:
            raise HTTPException(status_code=403, detail="Access Denied.")

    async def check_agent(self, current_user):
        if current_user.role.name != UserRole.AGENT:
            raise HTTPException(status_code=403, detail="Access Denied.")

    async def check_landlord_or_admin(self, current_user):
        if current_user.role.name not in {"Admin", "Landlord"}:
            raise HTTPException(status_code=403, detail="Access Denied")
    async def check_admin(self, current_user):
        if current_user.role.name != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Access Denied")
