from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Awaitable, Callable, List, Optional, TypedDict, TypeVar

import phonenumbers
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from core.get_db import Base
from models.enums import (
    RENT_PAYMENT_STATUS,
    SOLD_BY,
    BVNStatus,
    BVNVerificationProviders,
    Furnishing,
    GenderChoices,
    GlobalRole,
    HouseType,
    LetterType,
    NINVerificationProviders,
    NINVerificationStatus,
    PaymentProvider,
    PropertyTypes,
    RentCycle,
    ViewingStatus,
)
from models.enums import UserRole as Role
from models.utils import calculate_expiry

ModelT = TypeVar("ModelT", bound=Base)
EventPublishHook = Callable[[ModelT, uuid.UUID], Awaitable[None]]


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: GlobalRole

    @field_validator("username")
    @classmethod
    def validate_username_length(cls, value: str):
        if not value:
            raise ValueError("Username cannot be empty.")
        if len(value) < 5:
            raise ValueError("Username must be at least 5 characters long.")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None and v not in Role:
            raise ValueError("Invalid role choice")
        return v


class UserCreate(UserBase):
    first_name: str = Field(..., min_length=3)
    last_name: str = Field(..., min_length=3)
    middle_name: str = Field(..., min_length=3)
    username: str = Field(..., min_length=5, max_length=20)
    password: str = Field(
        ..., min_length=7, json_schema_extra={"type": "string", "format": "password"}
    )
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str):
        try:
            parsed = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number. Use full international format.")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except Exception:
            raise ValueError("Invalid phone number format. Use e.g. +2348012345678")

    @field_validator("first_name", "last_name", "middle_name", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        return value.strip().title()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        errors = []
        if len(v) < 7:
            errors.append("≥7 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("lowercase letter")
        if not re.search(r"\d", v):
            errors.append("number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("special character")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v

    @model_validator(mode="after")
    def finalize_fields(self):
        if not self.username:
            object.__setattr__(self, "username", self.email.split("@")[0])
        # object.__setattr__(self, "name", f"{self.firstName} {self.lastName}".strip())
        return self

    @field_validator("first_name")
    @classmethod
    def validate_firstname_length(cls, value: str):
        if not value:
            raise ValueError("First Name cannot be empty.")
        if len(value) < 5:
            raise ValueError("First Name must be at least 5 characters long.")
        return value

    @field_validator("last_name")
    @classmethod
    def validate_lastname_length(cls, value: str):
        if not value:
            raise ValueError("Last Name cannot be empty.")
        if len(value) < 5:
            raise ValueError("Last Name must be at least 5 characters long.")
        return value


class UserLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., min_length=7, json_schema_extra={"type": "string", "format": "password"}
    )

    # @field_validator("email", mode="before")
    # @classmethod
    # def normalize_email(cls, value: str) -> str:
    #     return value.strip().lower()


class UserPublicSchema(BaseModel):
    id: uuid.UUID
    first_name: str
    middle_name: str
    last_name: str
    username: str
    email: str
    phone_number: Optional[str]

    model_config = {"from_attributes": True}


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: Optional[str] = None
    otp: Optional[str] = None
    new_password: str

    @model_validator(mode="before")
    @classmethod
    def validate_token_or_otp(cls, values):
        token = values.get("token")
        otp = values.get("otp")
        if not token and not otp:
            raise ValueError("Either token or otp must be provided")
        return values


class UserProfileSchema(BaseModel):
    state_of_birth: str
    occupation: str
    address: str
    gender: GenderChoices
    date_of_birth: date
    public_id: str
    nin: str
    bvn: str
    account_number: str
    bank_name: str
    profile_pic_path: str
    nin_verification_provider: NINVerificationProviders
    bvn_verification_provider: BVNVerificationProviders

    @field_validator("nin_verification_provider")
    @classmethod
    def validate_nin_provider(cls, v):
        if v is not None and v not in NINVerificationProviders:
            raise ValueError("Invalid Nin Verification provider")
        return v

    @field_validator("bvn_verification_provider")
    @classmethod
    def validate_bvn_provider(cls, v):
        if v is not None and v not in BVNVerificationProviders:
            raise ValueError("Invalid BVN  Verification provider")
        return v


class ReVerifyNin(BaseModel):
    nin: str
    nin_verification_provider: NINVerificationProviders

    @field_validator("nin_verification_provider")
    @classmethod
    def validate_nin_provider(cls, v):
        if v is not None and v not in NINVerificationProviders:
            raise ValueError("Invalid Nin Verification provider")
        return v


class ReVerifyBVN(BaseModel):
    bvn: str
    bvn_verification_provider: BVNVerificationProviders

    @field_validator("bvn_verification_provider")
    @classmethod
    def validate_bvn_provider(cls, v):
        if v is not None and v not in BVNVerificationProviders:
            raise ValueError("Invalid BVN  Verification provider")
        return v


class ReVerifyAccountNumber(BaseModel):
    account_number: str
    bank_code: str


class UserProfileSchemaOut(BaseModel):
    user: UserPublicSchema
    id: uuid.UUID
    state_of_birth: str
    occupation: str
    address: str
    gender: GenderChoices
    date_of_birth: date
    profile_pic_path: str
    nin_verification_status: NINVerificationStatus
    bvn_status: BVNStatus
    nin_verified: bool
    bvn_verified: bool
    bvn_verified_at: Optional[datetime] = None
    nin_verified_at: Optional[datetime] = None
    bvn_verification_provider: BVNVerificationProviders
    nin_verification_provider: NINVerificationProviders
    model_config = {"from_attributes": True}


class UserProfileUpdateSchema(BaseModel):
    profile_pic_path: str | None = None
    public_id: str | None = None
    date_of_birth: date | None = None
    gender: GenderChoices | None = None
    address: str | None = None
    occupation: str | None = None
    state_of_birth: str | None = None


class ImageDeleteResourceSchema(BaseModel):
    resource_type: str = "images"


class RawDeleteResourceSchema(BaseModel):
    resource_type: str = "raw"


class CloudinaryUploadRequest(BaseModel):
    secure_url: str
    public_id: str


class CloudinaryPDFUploadRequest(BaseModel):
    secure_url: str
    public_id: str


class RentPoofSchema(CloudinaryPDFUploadRequest):
    property_id: uuid.UUID
    amount_paid: Decimal


class CloudinaryUpdateRequest(BaseModel):
    secure_url: str
    public_id: str


class UploadImageResponse(BaseModel):
    id: uuid.UUID
    url: str
    public_id: str


class MarkAsSoldSchema(BaseModel):
    sold_by: SOLD_BY

    @field_validator("sold_by")
    @classmethod
    def validate_sold_by(cls, v):
        if v is not None and v not in SOLD_BY:
            raise ValueError("Not allowed")
        return v


class PropertyBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str]
    address: str
    rooms: int
    bathrooms: Optional[int] = 1
    toilets: Optional[int] = 1

    default_rent_amount: Optional[int]
    default_rent_cycle: Optional[RentCycle]

    house_type: HouseType
    property_type: PropertyTypes

    square_meters: Optional[int]
    is_owner: bool = True
    is_manager: bool = False
    managed_by_id: Optional[uuid.UUID] = None
    state_id: uuid.UUID
    lga_id: uuid.UUID

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        if v is not None and v not in PropertyTypes:
            raise ValueError("Invalid Property Type")
        return v

    @field_validator("house_type")
    @classmethod
    def validate_house_type(cls, v):
        if v is not None and v not in HouseType:
            raise ValueError("Invalid House Type")
        return v

    @field_validator("default_rent_amount")
    @classmethod
    def validate_rent(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Rent must be positive.")
        return v

    @field_validator("lga_id")
    @classmethod
    def validate_lga(cls, v):
        if not v:
            raise ValueError("LGA ID is required.")
        return v

    @field_validator("state_id")
    @classmethod
    def validate_state(cls, v):
        if not v:
            raise ValueError("State ID is required.")
        return v

    @field_validator("default_rent_cycle")
    @classmethod
    def validate_rent_cycle(cls, v):
        if v is not None and v not in RentCycle:
            raise ValueError("Invalid rent cycle.")
        return v

    @field_validator("is_manager")
    @classmethod
    def validate_manager(cls, v, info: ValidationInfo):
        if v and not info.data.get("managed_by_id"):
            raise ValueError("Managed property must have a manager.")
        return v

    @field_validator("is_owner")
    @classmethod
    def validate_owner(cls, v, info: ValidationInfo):
        if v and info.data.get("managed_by_id"):
            raise ValueError("Owner-managed property cannot have a manager assigned.")
        return v


class PropertyCreate(PropertyBase):
    pass


class CredentialAttestation(BaseModel):
    credential_id: str
    public_key: str
    device_fingerprint: str


class CredentialAttestationOut(BaseModel):
    id: uuid.UUID
    credential_id: str
    public_key: str
    device_fingerprint: str


class VerifyLoginRequest(BaseModel):
    credential_id: str


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    address: Optional[str] = None
    rooms: Optional[int] = None
    description: Optional[str] = None
    bathrooms: Optional[int] = None
    toilets: Optional[int] = None

    default_rent_amount: Optional[int] = None
    default_rent_cycle: Optional[RentCycle] = None

    house_type: Optional[HouseType] = None
    property_type: Optional[PropertyTypes] = None

    square_meters: Optional[int] = None
    is_owner: Optional[bool] = None
    is_manager: Optional[bool] = None
    managed_by_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_patch_rules(self):
        if self.default_rent_amount is not None:
            if self.default_rent_amount <= 0:
                raise ValueError("Rent must be positive.")

        if self.is_manager is True:
            if self.managed_by_id is None:
                raise ValueError("Managed property must have a manager.")

        if self.is_owner is True:
            if self.managed_by_id is not None:
                raise ValueError(
                    "Owner-managed property cannot have a manager assigned."
                )

        return self


class ResendEmailSchema(BaseModel):
    email: EmailStr


class PropertyBaseOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    address: str
    rooms: int
    bathrooms: Optional[int]
    toilets: Optional[int]
    square_meters: Optional[int]

    default_rent_amount: Optional[int]
    default_rent_cycle: Optional[str]

    house_type: str
    property_type: str

    is_owner: bool
    is_manager: bool
    is_occupied: bool
    is_available: bool
    is_verified: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    owner: uuid.UUID
    managed_by: Optional[uuid.UUID]

    state: Optional["StateBaseSchema"]
    lga: Optional["LgaBaseSchema"]

    images: List["ImageBaseSchema"] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @field_validator("owner", mode="before")
    @classmethod
    def owner_id(cls, v):
        if hasattr(v, "id"):
            return v.id
        return v

    @field_validator("managed_by", mode="before")
    @classmethod
    def manager_id(cls, v):
        if hasattr(v, "id"):
            return v.id
        return v


class PropertyOut(PropertyBaseOut):
    tenants: List["TenantBaseOut"] = Field(default_factory=list)


class ImageBaseSchema(BaseModel):
    image_path: HttpUrl
    model_config = {"from_attributes": True}


class LgaBaseSchema(BaseModel):
    name: str
    model_config = {"from_attributes": True}


class LgaSchema(LgaBaseSchema):
    id: uuid.UUID
    location: Optional[dict] = None
    model_config = {"from_attributes": True}


class StateBaseSchema(BaseModel):
    name: str
    model_config = {"from_attributes": True}


class StateSchema(StateBaseSchema):
    id: uuid.UUID
    location: Optional[dict] = None
    lgas: List[LgaSchema] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class EffectiveRent(TypedDict):
    rent_amount: Optional[int]
    rent_cycle: Optional[RentCycle]


class TenantBase(BaseModel):
    rent_amount: Optional[Decimal] = None
    # rent_cycle: Optional[RentCycle] = None
    rent_start_date: date

    first_name: str = Field(..., min_length=5)
    middle_name: str = Field(..., min_length=5)
    last_name: str = Field(..., min_length=5)
    matched_user_name: str | None = None

    @field_validator("rent_amount")
    @classmethod
    def validate_rent(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Rent must be positive.")
        return v

    @model_validator(mode="before")
    @classmethod
    def add_matched_user_name(cls, obj):
        if hasattr(obj, "matched_user") and obj.matched_user:
            user = obj.matched_user
            return {
                **obj.__dict__,
                "matched_user_name": (
                    f"{user.first_name} {user.middle_name or ''} {user.last_name}"
                ).strip(),
            }

        if isinstance(obj, dict):
            return obj

        return obj

    @field_validator("first_name", "middle_name", "last_name", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        return value.strip().title()

    @model_validator(mode="after")
    def validate_dates(self):
        if not self.rent_start_date:
            raise ValueError("rent_start_date is required")
        return self


class TenantCreate(TenantBase):
    property_id: uuid.UUID
    # matched_user_name: Optional[str] = Field(
    #     None, description="first or last name of user to match"
    # )


class TenantUpdate(BaseModel):
    rent_amount: Optional[Decimal] = None
    rent_cycle: Optional[RentCycle] = None
    rent_start_date: Optional[date] = None
    rent_expiry_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_partial(self):
        if self.rent_start_date and self.rent_expiry_date:
            if self.rent_expiry_date < self.rent_start_date:
                raise ValueError("rent_expiry_date must be after rent_start_date")

        if self.rent_amount is not None and self.rent_amount < 0:
            raise ValueError("rent_amount must be positive")

        return self

    @field_validator("rent_amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("rent_amount must be positive")
        return v


class TenantBaseOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    first_name: str
    middle_name: str
    last_name: str
    phone_number: Optional[str] = None
    matched_user_id: Optional[uuid.UUID] = None
    rent_amount: Optional[Decimal] = None
    rent_cycle: Optional[RentCycle] = None
    rent_start_date: date
    rent_expiry_date: Optional[date] = None
    is_active: bool

    model_config = {"from_attributes": True}


class PaymentProofOut(BaseModel):
    file_path: str
    model_config = {"from_attributes": True}


class RentReceiptOut(BaseModel):
    receipt_path: str
    payment_proof: Optional["RentProofBaseOut"] = None
    model_config = {"from_attributes": True}


class TenantWithPropertyOut(TenantBaseOut):
    property: Optional[PropertyBaseOut] = None
    rent_receipts: list[RentReceiptOut] = []
    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def dates_consistency(self):
        if self.rent_start_date and self.rent_expiry_date:
            if self.rent_expiry_date < self.rent_start_date:
                raise ValueError("rent_expiry_date must be after rent_start_date")
        return self

    @model_validator(mode="after")
    def prepare_defaults(self):
        if not self.rent_cycle and self.property:
            self.rent_cycle = self.property.default_rent_cycle

        if not self.rent_amount and self.property:
            self.rent_amount = self.property_obj.default_rent_amount

        if not self.rent_expiry_date and self.rent_start_date and self.rent_cycle:
            self.rent_expiry_date = calculate_expiry(
                self.rent_start_date, self.rent_cycle
            )

        return self

    # @computed_field
    # @property
    # def effective_rent(self) -> EffectiveRent:
    #     amount = self.rent_amount
    #     if amount is None and self.property_obj:
    #         amount = self.property_obj.default_rent_amount

    #     cycle = self.rent_cycle
    #     if cycle is None and self.property_obj:
    #         cycle = self.property_obj.default_rent_cycle

    #     return {
    #         "rent_amount": amount,
    #         "rent_cycle": cycle,
    #     }


class SalesListingSchema(BaseModel):
    price: Decimal
    plot_size: Decimal
    parking_spaces: int

    title: str
    address: str
    description: str
    parking_spaces: int

    state_id: Optional[uuid.UUID]
    lga_id: Optional[uuid.UUID]

    is_available: bool

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal):
        if v <= 10_000:
            raise ValueError("Price must be greater than 10,000")
        return v

    @field_validator("plot_size")
    @classmethod
    def validate_plot_size(cls, v: Decimal):
        if v <= 100:
            raise ValueError("Plot size must be greater than 100sqm")
        return v


class SalesListingUpdateSchema(BaseModel):
    price: Decimal | None = None
    plot_size: Decimal | None = None
    parking_spaces: int | None = None
    title: str | None = None
    description: str | None = None
    address: str | None = None
    
    bathrooms: int | None = None
    toilets: int | None = None
    state_id: uuid.UUID | None = None
    lga_id: uuid.UUID | None = None
    
    contact_phone: str | None = None
    

    @field_validator("parking_spaces")
    @classmethod
    def validate_parking_spaces(cls, v: int):
        if v < 0:
            raise ValueError("Parking spaces cannot be negative")
        if v > 15:
            raise ValueError("Parking spaces limit exceeded")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal):
        if v is not None:
            if v <= 10_000:
                raise ValueError("Price must be greater than 10,000")
            return v

    @field_validator("plot_size")
    @classmethod
    def validate_plot_size(cls, v: Decimal):
        if v is not None:
            if v <= 100:
                raise ValueError("Plot size must be greater than 100sqm")
            return v


class RentalListingSchema(BaseModel):
    has_water: bool
    has_electricity: bool
    rent_amount: Decimal
    rent_cycle: RentCycle
    rent_duration: RentCycle
    title: str
    address: str
    description: str
    parking_spaces: int
    state_id: Optional[uuid.UUID]
    lga_id: Optional[uuid.UUID]
    is_available: bool
    is_verified: bool
    house_type: HouseType
    property_type: PropertyTypes
    slug: Optional[str]
    expires_at: Optional[datetime]
    furnished_level: Furnishing
    bathrooms: int
    toilets: int
    rooms: int

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        if v is not None and v not in PropertyTypes:
            raise ValueError("Invalid Property Type")
        return v

    @field_validator("house_type")
    @classmethod
    def validate_house_type(cls, v):
        if v is not None and v not in HouseType:
            raise ValueError("Invalid House Type")
        return v

    @field_validator("furnished_level")
    @classmethod
    def validate_furnishing_type(cls, v):
        if v is not None and v not in Furnishing:
            raise ValueError("Invalid Furnishing Level")
        return v

    @field_validator("description", "title", "address", "slug", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        return value.strip().title()

    @field_validator("rent_amount", mode="before")
    @classmethod
    def validate_price(cls, v: Decimal):
        if v <= 5000:
            raise ValueError("Price must be greater than 5000")
        if v >= 50_000_000:
            raise ValueError("Price limit exceeded")

        return v

    @field_validator("parking_spaces", mode="before")
    @classmethod
    def validate_parking_spaces(cls, v: int):
        if v < 0:
            raise ValueError("Parking spaces cannot be negative")
        if v > 15:
            raise ValueError("Parking spaces limit exceeded")
        return v

    @field_validator("expires_at", mode="after")
    @classmethod
    def validate_expiry(cls, v: Optional[datetime]):
        if v is None:
            return v
        # Convert naive datetime to UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("Expiry date must be in the future")
        return v

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: Optional[str]):
        if v:
            v = v.strip().lower().replace(" ", "-")
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError(
                    "Slug can only contain lowercase letters, numbers, and hyphens"
                )
        return v

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str):
        if len(v) < 5:
            raise ValueError("Title must be at least 5 characters long")
        return v


class RentalListingUpdateSchema(BaseModel):
    has_water: bool | None = None
    has_electricity: bool | None = None
    rent_amount: Decimal | None = None
    rent_cycle: RentCycle | None = None
    title: str | None = None
    address: str | None = None
    description: str | None = None
    parking_spaces: int | None = None
    state_id: uuid.UUID | None = None
    lga_id: uuid.UUID | None = None
    house_type: HouseType | None = None
    property_type: PropertyTypes | None = None
    slug: str | None = None
    expires_at: datetime | None = None
    furnished_level: Furnishing | None = None

    @field_validator("description", "title", "address", "slug", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        if value is not None:
            return value.strip().title()

    @field_validator("rent_amount", mode="before")
    @classmethod
    def validate_price(cls, v: Decimal):
        if v is not None:
            if v <= 10:
                raise ValueError("Price must be greater than 10")
            return v

    @field_validator("parking_spaces", mode="before")
    @classmethod
    def validate_parking_spaces(cls, v: int):
        if v is not None:
            if v < 0:
                raise ValueError("Parking spaces cannot be negative")
            return v

    @field_validator("expires_at", mode="after")
    @classmethod
    def validate_expiry(cls, v: Optional[datetime]):
        if v is not None:
            # Convert naive datetime to UTC
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry date must be in the future")
            return v

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: Optional[str]):
        if v is not None:
            if v:
                v = v.strip().lower().replace(" ", "-")
                if not re.match(r"^[a-z0-9-]+$", v):
                    raise ValueError(
                        "Slug can only contain lowercase letters, numbers, and hyphens"
                    )
            return v

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str):
        if v is not None:
            if len(v) < 5:
                raise ValueError("Title must be at least 5 characters long")
            return v


class RentalListingOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    address: str

    rent_amount: Decimal
    rent_cycle: RentCycle
    parking_spaces: int

    has_water: bool
    has_electricity: bool
    house_type: HouseType
    property_type: PropertyTypes
    furnished_level: Furnishing

    is_available: bool
    is_verified: bool

    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    images: List["ImageBaseSchema"] = Field(
        default_factory=list,
        validation_alias="gallery",
        serialization_alias="images",
    )
    state: Optional["StateBaseSchema"]
    lga: Optional["LgaBaseSchema"]

    model_config = {"from_attributes": True}


class SalesListingOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    address: str
    parking_spaces: int

    price: Decimal
    plot_size: Decimal
    contact_phone: str
    parking_spaces: int

    is_available: bool
    is_verified: bool

    created_at: datetime
    updated_at: datetime

    images: List["ImageBaseSchema"] = Field(
        default_factory=list,
        validation_alias="gallery",
        serialization_alias="images",
    )
    state: Optional["StateBaseSchema"]
    lga: Optional["LgaBaseSchema"]

    model_config = {"from_attributes": True}


class PaginatedSalesListing(BaseModel):
    items: list["SalesListingOut"]
    page: int
    per_page: int
    total: int


class RejectProofSchema(BaseModel):
    reason: str


class RentProofBaseOut(BaseModel):
    id: uuid.UUID
    file_path: str
    status: RENT_PAYMENT_STATUS
    uploaded_at: datetime
    model_config = {"from_attributes": True}


class RentProofOut(RentProofBaseOut):
    public_id: str
    tenant: Optional["TenantBaseOut"] = None
    property: Optional["PropertyBaseOut"] = None
    model_config = {"from_attributes": True}


@dataclass(frozen=True)
class PaymentVerificationResult:
    receipt_id: uuid.UUID
    amount: float
    month_paid_for: int
    year_paid_for: int
    tenant_name: str
    property_id: uuid.UUID


class RentReceiptBaseOut(BaseModel):
    id: uuid.UUID
    amount: Decimal
    month_paid_for: int
    year_paid_for: int
    receipt_path: Optional[HttpUrl] = None

    created_at: datetime

    reference_number: str
    barcode_reference: str
    tenant: Optional["TenantBaseOut"] = None
    property: Optional["PropertyBaseOut"] = None
    payment_proof: Optional[RentProofBaseOut] = None

    model_config = {"from_attributes": True}


class MultiUploadRequest(BaseModel):
    count: Annotated[int, Field(gt=0, le=3)]


class UploadDeleteRequest(BaseModel):
    public_ids: List[str]
   


class UploadSingleDeleteRequest(BaseModel):
    public_id: str
    resource_type: str


class EncryptedMessageCreate(BaseModel):
    # conversation_id: uuid.UUID
    ciphertext: str
    nonce: str
    sender_public_key: str


class EncryptedMessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    ciphertext: str
    nonce: str
    sender_public_key: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleViewingIn(BaseModel):
    viewing_date: datetime


class SaleConversationOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    created_at: datetime
    viewing_date: Optional[datetime]
    viewing_status: ViewingStatus

    model_config = {"from_attributes": True}


class RentalConversationOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    renter_id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    viewing_date: Optional[datetime]
    viewing_status: ViewingStatus

    @field_validator("viewing_status")
    @classmethod
    def validate_status_provider_type(cls, v):
        if v is not None and v not in ViewingStatus:
            raise ValueError("Invalid")
        return v

    model_config = {"from_attributes": True}


class MessageUserOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime

    sender: Optional["MessageUserOut"] = None
    receiver: Optional["MessageUserOut"] = None

    model_config = {"from_attributes": True}


class MessageCursorOut(MessageOut):
    ciphertext: str
    sender_id: uuid.UUID
    receiver_id: uuid.UUID

    is_read: bool
    read_at: datetime | None
    model_config = {"from_attributes": True}


class CursorPage(BaseModel):
    items: list[MessageCursorOut]
    next_cursor: datetime | None
    model_config = {"from_attributes": True}


class RentPaymentSchema(BaseModel):
    property_id: uuid.UUID
    payment_provider: PaymentProvider
    currency: str = "NGN"

    @field_validator("payment_provider")
    @classmethod
    def validate_payment_provider_type(cls, v):
        if v is not None and v not in PaymentProvider:
            raise ValueError("Invalid Property Type")
        return v


class RentPaymentVerifySchema(BaseModel):
    reference: str


class RentPaymentRefundSchema(BaseModel):
    payment_id: int


class BankOut(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}


class BaseImageOut(BaseModel):
    id: uuid.UUID
    image_path: str


class LetterWithTenantWithPropertyOut:
    id: uuid.UUID
    is_read: bool
    created_at: datetime
    tenant: Optional[TenantBaseOut] = None
    property: Optional[PropertyBaseOut] = None
    letter: list["LetterSchemaOut"] = []
    model_config = {"from_attributes": True}


class LetterRecipientOut(BaseModel):
    id: uuid.UUID
    is_read: bool
    created_at: datetime
    letter: LetterSchemaOut
    model_config = {"from_attributes": True}


class LetterUploadWithPDFSchema(BaseModel):
    file_path: str
    public_id: str
    letter_type: LetterType
    title: str

    @field_validator("letter_type")
    @classmethod
    def validate_letter_type(cls, v):
        if v is not None and v not in LetterType:
            raise ValueError("Invalid role choice")
        return v


class LetterUploadWithoutPDFSchema(BaseModel):
    letter_type: LetterType
    title: str
    body: str

    @field_validator("letter_type")
    @classmethod
    def validate_letter_type(cls, v):
        if v is not None and v not in LetterType:
            raise ValueError("Invalid role choice")
        return v


class LetterSchemaOut(BaseModel):
    body: str | None = None
    file_path: str | None = None
    public_id: Optional[str] = None
    letter_type: LetterType
    title: str
    created_at: datetime
    model_config = {"from_attributes": True}
