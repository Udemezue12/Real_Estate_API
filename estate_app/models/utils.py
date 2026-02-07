import re
from datetime import date

from dateutil.relativedelta import relativedelta

from .enums import RentCycle


def calculate_expiry(start_date: date, rent_cycle: str) -> date:
    cycle = (rent_cycle or "").strip().lower()

    if cycle == RentCycle.MONTHLY.value.lower():
        return start_date + relativedelta(months=1)

    if cycle == RentCycle.YEARLY.value.lower():
        return start_date + relativedelta(years=1)

    return start_date + relativedelta(months=1)


def slugify(value: str) -> str:
   
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    value = re.sub(r"^-+|-+$", "", value)
    return value


def normalize_phone(phone: str) -> str:
    clean = re.sub(r"[^\d+]", "", phone)

   
    if clean.startswith("0") and len(clean) == 11:
        return "+234" + clean[1:] 

    if clean.startswith("+"):
        return clean

    return clean
