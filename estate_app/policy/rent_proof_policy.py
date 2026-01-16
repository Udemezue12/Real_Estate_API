import uuid

from models.models import Tenant, Property


class ModelPolicy:
    @staticmethod
    async def can_mark_payment(tenant: Tenant, user_id: uuid.UUID) -> bool:
        if not tenant.property:
            return False

        return user_id in {
            tenant.property.owner_id,
            tenant.property.managed_by_id,
        }

    @staticmethod
    async def can_access_property(property: Property, user_id: uuid.UUID) -> bool:
        return property.owner_id == user_id or property.managed_by_id == user_id
