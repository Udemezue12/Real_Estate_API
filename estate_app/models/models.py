import re
import uuid
from datetime import date, datetime
from typing import List, Optional
from uuid import uuid4

from bcrypt import checkpw, gensalt, hashpw
from geoalchemy2 import Geography
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from core.get_db import Base

from .enums import (
    PDF_STATUS,
    RENT_PAYMENT_STATUS,
    SOLD_BY,
    AccountNumberVerificationStatus,
    AccountVerificationProviders,
    BVNStatus,
    BVNVerificationProviders,
    Furnishing,
    GenderChoices,
    HouseType,
    LetterType,
    NINVerificationProviders,
    NINVerificationStatus,
    PaymentProvider,
    PaymentStatus,
    PayoutStatus,
    PropertyTypes,
    RentCycle,
    RentDuration,
    UserRole,
    ViewingStatus,
)
from .shape import convert_location
from .utils import calculate_expiry


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    middle_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False, default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sale_sender_encrypted_message: Mapped[List["SaleEncryptedMessage"]] = relationship(
        "SaleEncryptedMessage",
        back_populates="sender",
        foreign_keys="SaleEncryptedMessage.sender_id",
        cascade="all, delete-orphan",
    )
    sale_receiver_encrypted_message: Mapped[List["SaleEncryptedMessage"]] = (
        relationship(
            "SaleEncryptedMessage",
            back_populates="receiver",
            foreign_keys="SaleEncryptedMessage.receiver_id",
            cascade="all, delete-orphan",
        )
    )
    rental_sender_encrypted_message: Mapped[List["RentalEncryptedMessage"]] = (
        relationship(
            "RentalEncryptedMessage",
            back_populates="sender",
            foreign_keys="RentalEncryptedMessage.sender_id",
            cascade="all, delete-orphan",
        )
    )
    rental_receiver_encrypted_message: Mapped[List["RentalEncryptedMessage"]] = (
        relationship(
            "RentalEncryptedMessage",
            back_populates="receiver",
            foreign_keys="RentalEncryptedMessage.receiver_id",
            cascade="all, delete-orphan",
        )
    )
    property_buyer: Mapped[List["SaleConversation"]] = relationship(
        "SaleConversation",
        back_populates="buyer",
        foreign_keys="SaleConversation.buyer_id",
        cascade="all, delete-orphan",
    )
    property_seller: Mapped[List["SaleConversation"]] = relationship(
        "SaleConversation",
        back_populates="seller",
        foreign_keys="SaleConversation.seller_id",
        cascade="all, delete-orphan",
    )
    property_renter: Mapped[List["RentalConversation"]] = relationship(
        "RentalConversation",
        back_populates="renter",
        foreign_keys="RentalConversation.renter_id",
        cascade="all, delete-orphan",
    )
    property_owner: Mapped[List["RentalConversation"]] = relationship(
        "RentalConversation",
        back_populates="owner",
        foreign_keys="RentalConversation.owner_id",
        cascade="all, delete-orphan",
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )

    properties: Mapped[List["Property"]] = relationship(
        "Property",
        back_populates="owner",
        foreign_keys="Property.owner_id",
        cascade="all, delete-orphan",
    )
    managed_properties: Mapped[List["Property"]] = relationship(
        "Property", back_populates="managed_by", foreign_keys="Property.managed_by_id"
    )

    rental_listings: Mapped[List["RentalListing"]] = relationship(
        "RentalListing",
        back_populates="listed_by",
        foreign_keys="RentalListing.listed_by_id",
        cascade="all, delete-orphan",
    )

    sales_created: Mapped[List["SaleListing"]] = relationship(
        "SaleListing",
        back_populates="listed_by",
        foreign_keys="SaleListing.listed_by_id",
        cascade="all, delete-orphan",
    )
    sales_by: Mapped[List["SaleListing"]] = relationship(
        "SaleListing",
        back_populates="seller",
        foreign_keys="SaleListing.sale_listed_by",
    )
    rent_by: Mapped[List["SaleListing"]] = relationship(
        "RentalListing",
        back_populates="renter",
        foreign_keys="RentalListing.rental_listed_by",
    )

    images_sales_created: Mapped[List["SaleListingImage"]] = relationship(
        "SaleListingImage",
        back_populates="creator",
        foreign_keys="SaleListingImage.sale_image_creator",
        cascade="all, delete-orphan",
    )
    images_sales_created_by: Mapped[List["SaleListingImage"]] = relationship(
        "SaleListingImage",
        back_populates="creator_by",
        foreign_keys="SaleListingImage.created_by_id",
    )
    images_rental_created: Mapped[List["RentalListingImage"]] = relationship(
        "RentalListingImage",
        back_populates="creator",
        foreign_keys="RentalListingImage.rental_image_creator",
        cascade="all, delete-orphan",
    )
    images_rental_created_by: Mapped[List["RentalListingImage"]] = relationship(
        "RentalListingImage",
        back_populates="creator_by",
        foreign_keys="RentalListingImage.created_by_id",
    )
    rent_payments_images_created_by: Mapped[List["RentPaymentProof"]] = relationship(
        "RentPaymentProof",
        back_populates="uploaded_by",
        foreign_keys="RentPaymentProof.created_by_id",
    )
    images_property_created_by: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage",
        back_populates="property_by",
        foreign_keys="PropertyImage.property_by_id",
    )
    images_property_created: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage",
        back_populates="property_creator",
        foreign_keys="PropertyImage.property_image_creator",
        cascade="all, delete-orphan",
    )

    rent_receipts: Mapped[List["RentReceipt"]] = relationship(
        "RentReceipt",
        back_populates="landlord",
        foreign_keys="RentReceipt.landlord_id",
        cascade="all, delete-orphan",
    )
    sent_letters = relationship(
        "Letter",
        back_populates="sender",
        cascade="all, delete-orphan",
    )

    credentials = relationship("PasskeyCredential", back_populates="user")

    def set_password(self, raw_password: str):
        salt = gensalt()
        self.hashed_password = hashpw(raw_password.encode("utf-8"), salt).decode(
            "utf-8"
        )

    def check_password(self, raw_password: str) -> bool:
        return checkpw(
            raw_password.encode("utf-8"), self.hashed_password.encode("utf-8")
        )

    def normalize(self) -> None:
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        self.first_name = self.first_name.strip().title()
        self.last_name = self.last_name.strip().title()

    def __repr__(self):
        return f"<User {self.username} ({self.id})>"

    @hybrid_property
    def full_name(self) -> str:
        parts = [
            self.first_name,
            self.middle_name,
            self.last_name,
        ]
        return " ".join(p for p in parts if p)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    flutterwave_account_name: Mapped[str] = mapped_column(
        String(255), nullable=True, index=True
    )
    paystack_account_name: Mapped[str] = mapped_column(
        String(255), nullable=True, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="profile", uselist=False)

    profile_pic_path: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    profile_pic_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    nin_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    account_number: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    bank_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    paystack_bank_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    flutterwave_bank_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    paystack_account_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    paystack_account_verification_error: Mapped[str] = mapped_column(
        Text, nullable=True
    )
    paystack_account_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    paystack_account_verification_status: Mapped[AccountNumberVerificationStatus] = (
        mapped_column(
            Enum(AccountNumberVerificationStatus, native_enum=False),
            default=AccountNumberVerificationStatus.PENDING,
            index=True,
            nullable=False,
        )
    )
    paystack_account_verification_provider: Mapped[AccountVerificationProviders] = (
        mapped_column(
            Enum(AccountVerificationProviders, native_enum=False),
            nullable=False,
            default=AccountVerificationProviders.NONE_YET,
        )
    )
    flutterwave_account_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    flutterwave_account_verification_error: Mapped[str] = mapped_column(
        Text, nullable=True
    )
    flutterwave_account_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    flutterwave_account_verification_status: Mapped[AccountNumberVerificationStatus] = (
        mapped_column(
            Enum(AccountNumberVerificationStatus, native_enum=False),
            default=AccountNumberVerificationStatus.PENDING,
            index=True,
            nullable=False,
        )
    )
    flutterwave_account_verification_provider: Mapped[AccountVerificationProviders] = (
        mapped_column(
            Enum(AccountVerificationProviders, native_enum=False),
            nullable=False,
            default=AccountVerificationProviders.NONE_YET,
        )
    )

    nin_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    bvn_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    nin_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    bvn_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, index=True
    )
    gender: Mapped[GenderChoices] = mapped_column(
        Enum(GenderChoices, native_enum=False),
        nullable=False,
        default=GenderChoices.MALE,
    )
    address: Mapped[str] = mapped_column(Text, nullable=False)
    nin_verification_error: Mapped[str] = mapped_column(Text, nullable=True)
    state_of_birth: Mapped[str] = mapped_column(String(60), nullable=False)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nin_verification_status: Mapped[NINVerificationStatus] = mapped_column(
        Enum(NINVerificationStatus, native_enum=False),
        default=NINVerificationStatus.PENDING,
        index=True,
        nullable=False,
    )
    nin_verification_provider: Mapped[NINVerificationProviders] = mapped_column(
        Enum(NINVerificationProviders, native_enum=False),
        nullable=False,
        default=NINVerificationProviders.NONE_YET,
    )
    bvn_status: Mapped[BVNStatus] = mapped_column(
        Enum(BVNStatus, native_enum=False),
        default=BVNStatus.PENDING,
        nullable=False,
        index=True,
    )

    bvn_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    bvn_verification_error: Mapped[str] = mapped_column(Text, nullable=True)
    bvn_verification_provider: Mapped[BVNVerificationProviders] = mapped_column(
        Enum(BVNVerificationProviders, native_enum=False),
        nullable=False,
        default=BVNVerificationProviders.NONE_YET,
    )
    profile_pic_uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow()
    )
    paystack_recipient_code = mapped_column(String(100), nullable=True, index=True)

    flutterwave_beneficiary_id = mapped_column(String(100), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    credential_id: Mapped[str] = mapped_column(String, nullable=False)
    public_key: Mapped[str] = mapped_column(String, nullable=False)
    device_fingerprint: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="credentials")

    __table_args__ = (
        UniqueConstraint("user_id", "credential_id", name="unique_user_credential"),
        UniqueConstraint("user_id", "device_fingerprint", name="unique_user_device"),
        UniqueConstraint("user_id", "public_key", name="unique_user_publickey"),
    )


class State(Base):
    __tablename__ = "states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True, index=True
    )

    lgas: Mapped[List["LocalGovernmentArea"]] = relationship(
        "LocalGovernmentArea", back_populates="state", cascade="all, delete-orphan"
    )
    properties: Mapped[List["Property"]] = relationship(
        "Property", back_populates="state", cascade="all, delete-orphan"
    )

    def __str__(self):
        return self.name

    def as_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "location": convert_location(self.location),
        }


class LocalGovernmentArea(Base):
    __tablename__ = "local_government_areas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    state_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("states.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped["State"] = relationship("State", back_populates="lgas")
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True, index=True
    )
    properties: Mapped[List["Property"]] = relationship(
        "Property", back_populates="lga"
    )

    def __str__(self):
        return self.name

    def as_dict(self, preload_state=None):
        state_obj = preload_state
        return {
            "id": str(self.id),
            "name": self.name,
            "state": state_obj.name if state_obj else None,
            "location": convert_location(self.location),
        }

    def to_dict(self, state=None):
        return {
            "id": str(self.id),
            "name": self.name,
            "state": state.name if state else (self.state.name if self.state else None),
            "location": convert_location(self.location),
        }


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner: Mapped["User"] = relationship(
        "User", back_populates="properties", foreign_keys=[owner_id]
    )

    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=True)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False)

    managed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    managed_by: Mapped[Optional["User"]] = relationship(
        "User", back_populates="managed_properties", foreign_keys=[managed_by_id]
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("states.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped["State"] = relationship("State", back_populates="properties")

    lga_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("local_government_areas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lga: Mapped["LocalGovernmentArea"] = relationship(
        "LocalGovernmentArea", back_populates="properties"
    )

    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    toilets: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    default_rent_amount: Mapped[Optional[int]] = mapped_column(Integer)
    default_rent_cycle: Mapped[Optional[str]] = mapped_column(String(20))

    house_type: Mapped[HouseType] = mapped_column(
        Enum(HouseType, native_enum=False),
        nullable=False,
        default=HouseType.THREE_BEDROOM_FLAT,
    )

    property_type: Mapped[PropertyTypes] = mapped_column(
        Enum(PropertyTypes, native_enum=False), nullable=False
    )

    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False
    )
    property_letters = relationship(
        "LetterRecipient", back_populates="property", cascade="all, delete-orphan"
    )

    images: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    tenants: Mapped[List["Tenant"]] = relationship(
        "Tenant", back_populates="property", cascade="all, delete-orphan"
    )
    rent_receipts: Mapped[List["RentReceipt"]] = relationship(
        "RentReceipt", back_populates="property", cascade="all, delete-orphan"
    )

    square_meters: Mapped[Optional[int]] = mapped_column(Integer)


class PropertyImage(Base):
    __tablename__ = "property_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property: Mapped["Property"] = relationship("Property", back_populates="images")

    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )
    property_image_creator: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_creator: Mapped["User"] = relationship(
        "User",
        back_populates="images_property_created",
        foreign_keys=[property_image_creator],
    )
    property_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_by: Mapped["User"] = relationship(
        "User",
        back_populates="images_property_created_by",
        foreign_keys=[property_by_id],
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False
    )

    def __repr__(self):
        return f"<PropertyImage property={self.property_id} uploaded_at={self.uploaded_at}>"

    def as_dict(self):
        return {
            "id": str(self.id),
            "listing_id": str(self.property_id),
            "image_path": self.image_path,
            "public_id": self.public_id,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property: Mapped["Property"] = relationship("Property", back_populates="tenants")

    first_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    middle_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)

    matched_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matched_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[matched_user_id]
    )
    matched_user_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )

    rent_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(12, 2))
    rent_cycle: Mapped[RentCycle] = mapped_column(
        Enum(RentCycle, native_enum=False), nullable=False, index=True
    )

    rent_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    rent_expiry_date: Mapped[date] = mapped_column(Date, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    letters = relationship(
        "LetterRecipient", back_populates="tenant", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False
    )

    rent_receipts: Mapped[List["RentReceipt"]] = relationship(
        "RentReceipt", back_populates="tenant", cascade="all, delete-orphan"
    )
    rent_ledgers: Mapped[List["RentLedger"]] = relationship(
        "RentLedger",
        back_populates="tenant",
        cascade="all, delete-orphan",
        order_by="RentLedger.created_at",
    )

    @validates("phone_number")
    def validate_phone(self, key, value):
        if not re.match(r"^\+?[0-9]{7,15}$", value):
            raise ValueError("Invalid phone number format.")
        return value

    def get_effective_rent(self):
        amount = self.rent_amount or (
            self.property.default_rent_amount if self.property else None
        )
        cycle = self.rent_cycle or (
            self.property.default_rent_cycle if self.property else None
        )
        return {"rent_amount": amount, "rent_cycle": cycle}

    def prepare_defaults(self):
        if not self.rent_cycle and self.property:
            self.rent_cycle = self.property.default_rent_cycle

        if not self.rent_amount and self.property:
            self.rent_amount = self.property.default_rent_amount

        if not self.rent_expiry_date:
            self.rent_expiry_date = calculate_expiry(
                self.rent_start_date, self.rent_cycle
            )

    @validates("rent_start_date", "rent_expiry_date")
    def validate_dates(self, key, value):
        if self.rent_start_date and self.rent_expiry_date:
            if self.rent_expiry_date <= self.rent_start_date:
                raise ValueError("Rent expiry date must be after start date.")
        return value

    @validates("rent_amount")
    def validate_amount(self, key, value):
        if value is not None and value <= 0:
            raise ValueError("Rent amount must be positive.")
        return value


class RentLedger(Base):
    __tablename__ = "rent_ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="rent_ledgers")

    event: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )


class RentReceipt(Base):
    __tablename__ = "rent_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id")
    )
    tenant = relationship("Tenant", back_populates="rent_receipts")
    payment_context = mapped_column(
        Enum("FULL_RENT", "HALF_RENT", "OUTSTANDING_BALANCE", name="payment_context"),
        default="FULL_RENT",
        nullable=False,
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id")
    )
    property = relationship("Property", back_populates="rent_receipts")
    receipt_path: Mapped[str] = mapped_column(String(512), nullable=True)

    landlord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    landlord = relationship("User", back_populates="rent_receipts")

    expected_amount = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid = mapped_column(Numeric(12, 2), nullable=False)
    remaining_balance = mapped_column(Numeric(12, 2), nullable=False)
    month_paid_for = mapped_column(Integer)
    year_paid_for = mapped_column(Integer)
    rent_duration_months = mapped_column(Integer)
    fully_paid: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reference_number = mapped_column(String(69), unique=True)
    barcode_reference = mapped_column(String(69), unique=True, nullable=True)
    pdf_status: Mapped[PDF_STATUS] = mapped_column(
        Enum(PDF_STATUS, native_enum=False),
        nullable=False,
        index=True,
        default=PDF_STATUS.PENDING,
    )

    public_id = mapped_column(String(255), unique=True, nullable=False, index=True)

    payment_proof = relationship(
        "RentPaymentProof",
        back_populates="rent_receipt",
        uselist=False,
    )
    payment_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=True
    )

    created_at = mapped_column(DateTime, default=datetime.utcnow())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "property_id",
            "month_paid_for",
            "year_paid_for",
            name="uq_rent_receipt_per_month",
        ),
    )


class RentalListing(Base):
    __tablename__ = "rental_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    has_water: Mapped[bool] = mapped_column(Boolean, default=True)
    has_electricity: Mapped[bool] = mapped_column(Boolean, default=True)

    listed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listed_by: Mapped["User"] = relationship(
        "User", back_populates="rental_listings", foreign_keys=[listed_by_id]
    )
    rental_listed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    renter: Mapped["User"] = relationship(
        "User", back_populates="rent_by", foreign_keys=[rental_listed_by]
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    state_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("states.id"), nullable=True
    )
    state: Mapped[Optional["State"]] = relationship("State")

    lga_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("local_government_areas.id"), nullable=True
    )
    lga: Mapped[Optional["LocalGovernmentArea"]] = relationship("LocalGovernmentArea")

    rent_duration: Mapped[RentDuration] = mapped_column(
        Enum(RentDuration, native_enum=False), nullable=False, index=True
    )
    furnished_level: Mapped[Furnishing] = mapped_column(
        Enum(Furnishing, native_enum=False), nullable=False, index=True
    )

    house_type: Mapped[HouseType] = mapped_column(
        Enum(HouseType, native_enum=False),
        nullable=False,
        default=HouseType.THREE_BEDROOM_FLAT,
        index=True,
    )
    property_type: Mapped[PropertyTypes] = mapped_column(
        Enum(PropertyTypes, native_enum=False), nullable=False, index=True
    )
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    toilets: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    rent_amount: Mapped[Numeric] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    rent_cycle: Mapped[RentCycle] = mapped_column(
        Enum(RentCycle, native_enum=False), nullable=False, index=True
    )
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow(),
        onupdate=datetime.utcnow(),
        nullable=False,
    )

    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    verified_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[verified_by_id]
    )

    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    gallery: Mapped[List["RentalListingImage"]] = relationship(
        "RentalListingImage", back_populates="listing", cascade="all, delete-orphan"
    )
    unavailable_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    available_again_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    def __repr__(self):
        return f"<RentalListing {self.title} - {self.address}>"


class RentPaymentProof(Base):
    __tablename__ = "rent_proofs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    tenant_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant = relationship("Tenant")

    property_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property = relationship("Property")

    rent_receipt_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rent_receipts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rent_receipt = relationship("RentReceipt", back_populates="payment_proof")
    amount_paid = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[RENT_PAYMENT_STATUS] = mapped_column(
        Enum(RENT_PAYMENT_STATUS, native_enum=False),
        default=RENT_PAYMENT_STATUS.PENDING,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    public_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_by_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    uploaded_by = relationship(
        "User",
        back_populates="rent_payments_images_created_by",
        foreign_keys=[created_by_id],
    )

    uploaded_at = mapped_column(DateTime, default=datetime.utcnow())


class RentalListingImage(Base):
    __tablename__ = "rental_listing_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rental_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing: Mapped["RentalListing"] = relationship(
        "RentalListing", back_populates="gallery"
    )
    rental_image_creator: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="images_rental_created",
        foreign_keys=[rental_image_creator],
    )
    creator_by: Mapped["User"] = relationship(
        "User", back_populates="images_rental_created_by", foreign_keys=[created_by_id]
    )
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False
    )

    def as_dict(self):
        return {
            "id": str(self.id),
            "listing_id": str(self.listing_id),
            "image_path": self.image_path,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SaleListing(Base):
    __tablename__ = "sale_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    listed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("states.id"), nullable=True
    )
    state: Mapped[Optional["State"]] = relationship("State")

    lga_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("local_government_areas.id"), nullable=True
    )
    lga: Mapped[Optional["LocalGovernmentArea"]] = relationship("LocalGovernmentArea")
    sale_listed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    listed_by: Mapped["User"] = relationship(
        "User", back_populates="sales_created", foreign_keys=[listed_by_id]
    )
    seller: Mapped["User"] = relationship(
        "User", back_populates="sales_by", foreign_keys=[sale_listed_by]
    )
    plot_size: Mapped[Numeric] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sold_by: Mapped[SOLD_BY] = mapped_column(
        Enum(SOLD_BY, native_enum=False),
        default=SOLD_BY.NOT_SOLD,
        index=True,
    )
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    price: Mapped[Numeric] = mapped_column(Numeric(15, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    toilets: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    gallery: Mapped[List["SaleListingImage"]] = relationship(
        "SaleListingImage", back_populates="listing", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SaleListing {self.title}>"


class SaleListingImage(Base):
    __tablename__ = "sale_listing_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_image_creator: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    listing: Mapped["SaleListing"] = relationship(
        "SaleListing", back_populates="gallery"
    )
    creator: Mapped["User"] = relationship(
        "User", back_populates="images_sales_created", foreign_keys=[sale_image_creator]
    )
    creator_by: Mapped["User"] = relationship(
        "User", back_populates="images_sales_created_by", foreign_keys=[created_by_id]
    )

    image_path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )

    def as_dict(self):
        return {
            "id": str(self.id),
            "listing_id": str(self.listing_id),
            "image_path": self.image_path,
            "public_id": self.public_id,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    __table_args__ = (Index("idx_blacklisted_token", "token"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    blacklisted_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SaleConversation(Base):
    __tablename__ = "sale_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_listings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    last_viewing_set_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    viewing_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    listing: Mapped["SaleListing"] = relationship("SaleListing")

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    viewing_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    buyer: Mapped["User"] = relationship(
        "User", back_populates="property_buyer", foreign_keys=[buyer_id]
    )
    seller: Mapped["User"] = relationship(
        "User", back_populates="property_seller", foreign_keys=[seller_id]
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())

    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_id", name="uq_listing_buyer"),
    )


class RentalConversation(Base):
    __tablename__ = "rental_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rental_listings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    last_viewing_set_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    viewing_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    listing: Mapped["RentalListing"] = relationship("RentalListing")
    viewing_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )

    renter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    renter: Mapped["User"] = relationship(
        "User", back_populates="property_renter", foreign_keys=[renter_id]
    )
    owner: Mapped["User"] = relationship(
        "User", back_populates="property_owner", foreign_keys=[owner_id]
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())

    __table_args__ = (
        UniqueConstraint("listing_id", "renter_id", name="uq_listing_renter"),
    )


class SaleEncryptedMessage(Base):
    __tablename__ = "sales_encrypted_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender: Mapped["User"] = relationship(
        "User", back_populates="sale_sender_encrypted_message", foreign_keys=[sender_id]
    )
    receiver: Mapped["User"] = relationship(
        "User",
        back_populates="sale_receiver_encrypted_message",
        foreign_keys=[receiver_id],
    )

    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sender_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    receiver_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class RentalEncryptedMessage(Base):
    __tablename__ = "rental_encrypted_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rental_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender: Mapped["User"] = relationship(
        "User",
        back_populates="rental_sender_encrypted_message",
        foreign_keys=[sender_id],
    )
    receiver: Mapped["User"] = relationship(
        "User",
        back_populates="rental_receiver_encrypted_message",
        foreign_keys=[receiver_id],
    )

    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sender_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    receiver_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class SalesViewingHistory(Base):
    __tablename__ = "sales_viewing_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    convo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    old_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )
    new_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class RentalViewingHistory(Base):
    __tablename__ = "rental_viewing_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    convo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rental_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    old_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )
    new_status: Mapped[ViewingStatus] = mapped_column(
        Enum(ViewingStatus),
        default=ViewingStatus.PENDING,
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    response: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow(),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User")

    __table_args__ = (UniqueConstraint("key", "user_id", name="uq_idempotency_key"),)

    def __repr__(self) -> str:
        return f"<IdempotencyKey key={self.key} user_id={self.user_id}>"


class RentInvoice(Base):
    __tablename__ = "rent_invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    landlord_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    landlord_profile_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id")
    )

    total_amount: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    amount_paid: Mapped[Optional[Numeric]] = mapped_column(Numeric(12, 2), default=0)

    is_fully_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, native_enum=False)
    )
    provider_reference: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("rent_invoices.id"))
    landlord_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    landlord_profile_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id")
    )

    tenant_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_email: Mapped[str] = mapped_column(String, nullable=False)
    landlord_phoneNumber: Mapped[str] = mapped_column(String(20), nullable=True)
    tenant_phoneNumber: Mapped[str] = mapped_column(String(20), nullable=True)

    landlord_email: Mapped[str] = mapped_column(String, nullable=False)
    tenant_firstname: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_lastname: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_middlename: Mapped[str] = mapped_column(String(255), nullable=False)
    landlord_firstname: Mapped[str] = mapped_column(String(255), nullable=False)
    landlord_lastname: Mapped[str] = mapped_column(String(255), nullable=False)
    landlord_middlename: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant = relationship("Tenant")
    property_owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    property_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property = relationship("Property")

    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, native_enum=False)
    )
    provider_reference: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )

    amount_received: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10))

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING,
    )

    created_at = mapped_column(DateTime, default=datetime.utcnow())


class LandlordPayout(Base):
    __tablename__ = "landlord_payouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    landlord_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus, native_enum=False),
        default=PayoutStatus.PENDING,
    )

    provider_reference: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_name = mapped_column(String, nullable=False, index=True)

    paystack_bank_code: Mapped[str] = mapped_column(String, nullable=True)
    flutterwave_bank_code: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (UniqueConstraint("name", name="uq_bank_canonical"),)


class Letter(Base):
    __tablename__ = "letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caretaker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sender: Mapped["User"] = relationship("User", back_populates="sent_letters")

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property: Mapped["Property"] = relationship("Property")

    letter_type: Mapped[LetterType] = mapped_column(
        Enum(LetterType, native_enum=False),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)

    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    public_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), index=True
    )

    recipients: Mapped[List["LetterRecipient"]] = relationship(
        "LetterRecipient",
        back_populates="letter",
        cascade="all, delete-orphan",
    )


class LetterRecipient(Base):
    __tablename__ = "letter_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    letter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("letters.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    letter: Mapped["Letter"] = relationship("Letter", back_populates="recipients")

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="letters")
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    property: Mapped["Property"] = relationship(
        "Property", back_populates="property_letters"
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())

    __table_args__ = (
        UniqueConstraint("letter_id", "tenant_id", name="uq_letter_tenant"),
    )
