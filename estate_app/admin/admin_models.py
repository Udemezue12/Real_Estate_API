import uuid
from tortoise import fields
from fastapi_admin.models import AbstractAdmin


class AdminUser(AbstractAdmin):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=255)
    is_superuser = fields.BooleanField(default=False)

    class Meta:
        table = "admin_users"
