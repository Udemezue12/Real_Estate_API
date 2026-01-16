from datetime import date

from dateutil.relativedelta import relativedelta
from models.enums import RentCycle


def calculate_expiry(start_date: date, rent_cycle: RentCycle) -> date:
    if rent_cycle == RentCycle.MONTHLY:
        return start_date + relativedelta(months=1)

    if rent_cycle == RentCycle.YEARLY:
        return start_date + relativedelta(years=1)

    return start_date + relativedelta(weeks=1)
