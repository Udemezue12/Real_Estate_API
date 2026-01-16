# create_piccolo_admin.py
import asyncio
from .admin_user import AdminUser
from passlib.hash import bcrypt   

async def run():
    hashed = bcrypt.hash("admin123")
    await AdminUser.create(username="admin", password=hashed, is_superuser=True)

if __name__ == "__main__":
    asyncio.run(run())
