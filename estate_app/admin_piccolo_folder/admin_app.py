from .admin_table import UserTable
from piccolo_admin.endpoints import create_admin

AdminApp =create_admin(
    tables=[UserTable],
    site_name="Real Estate Admin Panel",
    
)
