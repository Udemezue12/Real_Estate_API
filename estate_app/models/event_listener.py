import uuid

from slugify import slugify
from sqlalchemy import event

from security.security_generate import user_generate

from .enums import FLAT_ALIASES, SELF_CON_ALIASES, PropertyTypes
from .models import (
    RentalListing,
    RentReceipt,
    SaleListing,
    Tenant,
)


@event.listens_for(RentalListing, "before_insert")
def generate_slug(mapper, connection, target):
    if not target.slug:
        target.slug = slugify(f"{target.title}-{uuid.uuid4().hex[:8]}")


@event.listens_for(Tenant, "before_insert")
def set_defaults(mapper, connection, target):
    target.prepare_defaults()


@event.listens_for(SaleListing, "before_insert")
def add_slug(mapper, connection, target: SaleListing):
    if not target.slug:
        base = f"{target.title}-{uuid.uuid4().hex[:6]}"
        target.slug = slugify(base)


@event.listens_for(SaleListing, "before_insert")
@event.listens_for(SaleListing, "before_update")
def normalize_property_type(mapper, connection, target: SaleListing):
    if not target.property_type:
        return

    clean = str(target.property_type).lower().strip()

    if clean in SELF_CON_ALIASES:
        target.property_type = PropertyTypes.SELF_CON

    elif clean in FLAT_ALIASES:
        target.property_type = PropertyTypes.FLAT


@event.listens_for(SaleListing, "before_insert")
@event.listens_for(SaleListing, "before_update")
def title_capitalize(mapper, connection, target: SaleListing):
    if target.title:
        target.title = target.title.strip().title()


@event.listens_for(SaleListing, "before_insert")
@event.listens_for(SaleListing, "before_update")
def normalize_address(mapper, connection, target: SaleListing):
    if target.address:
        target.address = target.address.strip().title()


@event.listens_for(RentReceipt, "before_insert")
async def set_reference_numbers(mapper, connection, target: "RentReceipt"):
    if not target.reference_number:
        target.reference_number = await user_generate.generate_reference()
    if not target.barcode_reference:
        target.barcode_reference = await user_generate.generate_reference()
