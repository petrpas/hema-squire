import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RefundState, RegistrationState, UnpaidListTreatment


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    hr_id: int | None = None
    club: str | None = Field(default=None, max_length=200)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    display_name: str
    hr_id: int | None
    nationality: str | None
    club: str | None


class AccountUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    club: str | None = Field(default=None, max_length=200)


class HRBindIn(BaseModel):
    hr_id: int


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str


class DisciplineIn(BaseModel):
    code: str
    name: str | None = None
    capacity: int = Field(gt=0)
    fee: int = Field(ge=0)
    fee_early: int | None = Field(default=None, ge=0)


class DisciplineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    capacity: int
    fee: int
    fee_early: int | None


class TournamentCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")
    display_name: str = Field(min_length=1, max_length=200)
    date: datetime.date
    language: str = "cs"


class TournamentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    date: datetime.date | None = None
    language: str | None = None
    reservation_validity_days: int | None = Field(default=None, gt=0)
    reminder_day: int | None = Field(default=None, gt=0)
    amount_tolerance_percent: int | None = Field(default=None, ge=0, le=100)
    refundable_until: datetime.date | None = None
    bank_account: str | None = None
    fio_token: str | None = None
    unpaid_list_treatment: UnpaidListTreatment | None = None
    early_bird_until: datetime.date | None = None
    weapon_rental_fee: int | None = Field(default=None, ge=0)
    weapon_rental_fee_early: int | None = Field(default=None, ge=0)
    afterparty_fee: int | None = Field(default=None, ge=0)
    afterparty_fee_early: int | None = Field(default=None, ge=0)


class TournamentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    display_name: str
    date: datetime.date
    language: str
    reservation_validity_days: int
    reminder_day: int
    amount_tolerance_percent: int
    refundable_until: datetime.date | None
    bank_account: str | None
    unpaid_list_treatment: UnpaidListTreatment
    early_bird_until: datetime.date | None
    weapon_rental_fee: int
    weapon_rental_fee_early: int | None
    afterparty_fee: int
    afterparty_fee_early: int | None
    disciplines: list[DisciplineOut]


class OrganizerAdd(BaseModel):
    email: EmailStr


class RegisterIn(BaseModel):
    disciplines: list[str] = Field(min_length=1)
    weapon_rentals: list[str] = []
    afterparty: bool = False
    aftersparring: bool = False
    accommodation: str | None = None
    notes: str | None = None
    wait_for_all: bool = False


class RegistrationEntryOut(BaseModel):
    code: str
    is_substitute: bool
    queue_position: int | None


class RegistrationOut(BaseModel):
    state: RegistrationState
    vs: int
    total_amount: int
    expires_at: datetime.datetime | None
    registered_at: datetime.datetime
    weapon_rentals: list[str]
    afterparty: bool
    aftersparring: bool
    accommodation: str | None
    notes: str | None
    refundable: bool | None
    refund_state: RefundState
    entries: list[RegistrationEntryOut]


class AvailabilityOut(BaseModel):
    code: str
    capacity: int
    taken: int
    free: int
    queue_length: int


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    source: str
    date: datetime.date
    amount_cents: int
    currency: str
    vs: int | None
    message: str | None
    payer_name: str | None
    payer_account: str | None


class ParticipantOut(BaseModel):
    name: str
    club: str | None
    nationality: str | None
    disciplines: list[str]
    status: Literal["confirmed", "unconfirmed"]
