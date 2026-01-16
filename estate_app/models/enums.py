from enum import Enum


class UserRole(str, Enum):
    TENANT = "Tenant"
    LANDLORD = "Landlord"
    LAWYER = "Lawyer"
    CARETAKER = "Caretaker"
    AGENT = "Agent"
    SELLER = "Seller"
    ADMIN = "Admin"


class NINVerificationStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    FAILED = "Failed"


class ApplicationType(str, Enum):
    RENT = "Rent"
    LEASE = "Lease"
    BUY = "BUY"


class GenderChoices(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
class SOLD_BY(str, Enum):
    MYSELF = "Myself"
    SOMEONE_ELSE= "Someone Else"
    NOT_SOLD = "Not Sold"

class NINVerificationProviders(str, Enum):
    YOU_VERIFY = "YouVerify"
    QORE_ID = "QoreID"
    PREMBLY = "Prembly"
    NONE_YET = "None_Yet"


class BVNVerificationProviders(str, Enum):
    YOU_VERIFY = "YouVerify"
    QORE_ID = "QoreID"
    PREMBLY = "Prembly"
    NONE_YET = "None_Yet"


class ViewingStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    DECLINED = "Declined"
    CANCELLED = "Cancelled"


class RentCycleToMonths(int, Enum):
    MONTHLY = 1
    QUARTERLY = 3
    YEARLY = 12


class HouseType(str, Enum):
    SELF_CON = "Self Contain"
    ONE_BEDROOM_FLAT = "One Bedroom Flat"
    TWO_BEDROOM_FLAT = "Two Bedroom Flat"
    THREE_BEDROOM_FLAT = "Three Bedroom Flat"
    DUPLEX = "Duplex"
    BUNGALOW = "Bungalow"


class RentCycle(str, Enum):
    MONTHLY = "Monthly"
    YEARLY = "Yearly"
    QUARTERLY = "Quarterly"


class BVNStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class RentDuration(str, Enum):
    YEARLY = "Yearly"
    QUARTERLY = "Quarterly"
    MONTHLY = "Monthly"


class PropertyTypes(str, Enum):
    LAND = "Land"
    BUNGALOW = "Bungalow"
    DUPLEX = "Duplex"
    TERRACE = "Terrace"
    FLAT = "Flat"
    SELF_CON = "Self Contain"
    COMMERCIAL_BUILDING = "Commercial Building"
    OFFICE_SPACE = "Office Space"


# class RENT_PAYMENT_STATUS(str, Enum):
#     PENDING = "Pending"
#     PAID = "Paid"
#     REJECTED = "Rejected"
class RENT_PAYMENT_STATUS(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    REJECTED = "REJECTED"


class RentLedgerEvent(str, Enum):
    RENT_CREATED = "RENT_CREATED"
    RENT_RENEWED = "RENT_RENEWED"
    RENT_AMOUNT_CHANGED = "RENT_AMOUNT_CHANGED"
    RENT_EXPIRED = "RENT_EXPIRED"


class APPLICATION_STATUS(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    CONTACTED = "Contacted"


class PDF_STATUS(str, Enum):
    PENDING = "Pending"
    GENERATING = "Generating"
    FAILED = "Failed"
    READY = "Ready"


SELF_CON_ALIASES = {
    "self contain",
    "self con",
    "self contained room",
    "self contained",
    "self-contained",
    "single room",
    "Self Con",
    "Self Contain",
    "Self Contained",
    "Self Contained Room",
    "Single Room",
}
FLAT_ALIASES = {
    "flat",
    "apartment",
    "one bedroom flat",
    "two bedroom flat",
    "three bedroom flat",
}


class Furnishing(Enum):
    FURNISHED = "furnished"
    SEMI_FURNISHED = "semi_furnished"
    UNFURNISHED = "unfurnished"


class MessageStatus(str, Enum):
    TRUE = "True"
    FALSE = "False"
