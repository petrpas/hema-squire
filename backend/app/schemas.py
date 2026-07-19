import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.i18n import catalog
from app.models import (
    ExtraCategory,
    RefundState,
    RegistrationState,
    RequestState,
    Role,
    UnpaidListTreatment,
)


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    hr_id: int | None = None
    club: str | None = Field(default=None, max_length=200)
    language: str = "cs"

    @field_validator("language")
    @classmethod
    def _known_language(cls, value: str) -> str:
        if value not in catalog.available():
            raise ValueError("unsupported_language")
        return value


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    hr_id: int | None
    nationality: str | None
    club: str | None
    language: str
    role: Role
    # computed from settings.owner_email, not stored (deployment Owner)
    is_deployment_owner: bool = False


class PleaIn(BaseModel):
    message: str | None = Field(default=None, max_length=1000)


class PleaOut(BaseModel):
    """The account's own latest plea; state is None when it has never pled."""

    state: RequestState | None
    message: str | None
    created_at: datetime.datetime | None
    decided_at: datetime.datetime | None


class AccountUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    club: str | None = Field(default=None, max_length=200)
    language: str | None = None

    @field_validator("language")
    @classmethod
    def _known_language(cls, value: str | None) -> str | None:
        if value is not None and value not in catalog.available():
            raise ValueError("unsupported_language")
        return value


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
    fee: int | None = Field(default=None, ge=0)
    fee_early: int | None = Field(default=None, ge=0)


class DisciplineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    capacity: int
    fee: int | None
    fee_early: int | None


class ExtraItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: ExtraCategory
    price: int = Field(ge=0)
    max_qty: int = Field(default=1, ge=1)


class ExtraItemOut(ExtraItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


# discount scopes may target the implicit discipline category or any extra category
ScopeCategory = Literal["discipline", "seminar", "rental", "afterparty", "merch"]


class DiscountCondition(BaseModel):
    kind: Literal["discipline_count", "early"]
    count: int | None = Field(default=None, ge=1)
    until: datetime.date | None = None

    @model_validator(mode="after")
    def _kind_fields(self) -> DiscountCondition:
        if self.kind == "discipline_count" and self.count is None:
            raise ValueError("discipline_count condition requires count")
        if self.kind == "early" and self.until is None:
            raise ValueError("early condition requires until")
        return self

    # discounts land in a JSON column via model_dump(); dates must be ISO strings
    @field_serializer("until")
    def _until_iso(self, until: datetime.date | None) -> str | None:
        return until.isoformat() if until else None


class DiscountEffect(BaseModel):
    kind: Literal["fixed", "percent"]
    value: int = Field(ge=0)

    @model_validator(mode="after")
    def _percent_bounds(self) -> DiscountEffect:
        if self.kind == "percent" and self.value > 100:
            raise ValueError("percent discount cannot exceed 100")
        return self


class DiscountIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    condition: DiscountCondition
    effect: DiscountEffect
    scope: list[ScopeCategory] = ["discipline"]


class TournamentCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")
    display_name: str = Field(min_length=1, max_length=200)
    date: datetime.date
    language: str = "cs"


class TournamentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    date: datetime.date | None = None
    language: str | None = None
    location: str | None = Field(default=None, max_length=300)
    organizer_names: list[str] | None = None
    registration_opens: datetime.date | None = None
    registration_closes: datetime.date | None = None
    discounts: list[DiscountIn] | None = None
    reservation_validity_days: int | None = Field(default=None, gt=0)
    reminder_day: int | None = Field(default=None, gt=0)
    amount_tolerance_percent: int | None = Field(default=None, ge=0, le=100)
    refundable_until: datetime.date | None = None
    bank_account: str | None = None
    fio_token: str | None = None
    unpaid_list_treatment: UnpaidListTreatment | None = None
    output_sheet_url: str | None = None
    hr_category_map: dict[str, str] | None = None
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
    owner_id: int | None
    cancelled_at: datetime.datetime | None
    reservation_validity_days: int
    reminder_day: int
    amount_tolerance_percent: int
    refundable_until: datetime.date | None
    bank_account: str | None
    unpaid_list_treatment: UnpaidListTreatment
    output_sheet_url: str | None
    hr_category_map: dict[str, str]
    early_bird_until: datetime.date | None
    weapon_rental_fee: int
    weapon_rental_fee_early: int | None
    afterparty_fee: int
    afterparty_fee_early: int | None
    location: str | None
    organizer_names: list[str]
    registration_opens: datetime.date | None
    registration_closes: datetime.date | None
    discounts: list[DiscountIn]
    extra_items: list[ExtraItemOut] = []
    # filled by the detail endpoint from setup.setup_missing(); None elsewhere
    setup_missing: list[str] | None = None
    disciplines: list[DisciplineOut]


class TeamAdd(BaseModel):
    email: EmailStr


class TeamMemberOut(BaseModel):
    fencer_id: int
    email: EmailStr
    display_name: str


class OwnerTransferIn(BaseModel):
    email: EmailStr


class AdminOwnerAssignIn(BaseModel):
    email: EmailStr


class AdminAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    hr_id: int | None
    is_deployment_owner: bool = False
    has_pending_plea: bool = False


class RoleUpdateIn(BaseModel):
    role: Role


class PleaQueueOut(BaseModel):
    id: int
    fencer_id: int
    email: EmailStr
    display_name: str
    message: str | None
    created_at: datetime.datetime


class PleaDecisionOut(BaseModel):
    id: int
    state: RequestState


class ExtraSelectionIn(BaseModel):
    extra_item_id: int
    qty: int = Field(default=1, ge=1)


class RegisterIn(BaseModel):
    disciplines: list[str] = Field(min_length=1)
    weapon_rentals: list[str] = []
    afterparty: bool = False
    aftersparring: bool = False
    accommodation: str | None = None
    notes: str | None = None
    wait_for_all: bool = False
    extras: list[ExtraSelectionIn] = []


class RegistrationEntryOut(BaseModel):
    code: str
    is_substitute: bool
    queue_position: int | None


class RegistrationExtraOut(BaseModel):
    extra_item_id: int
    name: str
    category: ExtraCategory
    qty: int


class RegistrationOut(BaseModel):
    state: RegistrationState
    vs: int
    total_amount: int
    expires_at: datetime.datetime | None
    registered_at: datetime.datetime
    paid_at: datetime.datetime | None
    weapon_rentals: list[str]
    afterparty: bool
    aftersparring: bool
    accommodation: str | None
    notes: str | None
    refundable: bool | None
    refund_state: RefundState
    extras: list[RegistrationExtraOut] = []
    entries: list[RegistrationEntryOut]


class AvailabilityOut(BaseModel):
    code: str
    capacity: int
    taken: int
    free: int
    queue_length: int


class PricePreviewIn(BaseModel):
    disciplines: list[str] = Field(min_length=1)
    weapon_rentals: list[str] = []
    afterparty: bool = False
    extras: list[ExtraSelectionIn] = []


class PricePreviewOut(BaseModel):
    total: int


class PaymentInstructionsOut(BaseModel):
    amount: int
    iban: str
    vs: int
    message: str
    expires_at: datetime.datetime | None
    spayd: str
    qr_png_base64: str


class OpenDisciplineOut(BaseModel):
    code: str
    name: str
    fee: int | None
    taken: int
    capacity: int
    queue_length: int


RegistrationStatus = Literal["open", "opens_on", "closed"]
MyRegistrationState = Literal["none", "reserved", "paid", "substitute", "cancelled"]


class OpenTournamentOut(BaseModel):
    slug: str
    display_name: str
    date: datetime.date
    location: str | None
    organizer_names: list[str]
    registration_status: RegistrationStatus
    registration_opens_on: datetime.date | None = None
    disciplines: list[OpenDisciplineOut]
    my_registration_state: MyRegistrationState


class PastTournamentOut(OpenTournamentOut):
    organized: bool


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
    status: str | None
    status_reason: str | None
    matched_registration_id: int | None


class LinkIn(BaseModel):
    transaction_id: int
    vs: list[int] = Field(min_length=1)


class IngestAndMatchOut(BaseModel):
    new: int
    duplicate: int
    matched: int
    flagged: int
    unmatched: int


class RuleIn(BaseModel):
    phase: str = Field(max_length=20)
    kind: str = Field(max_length=30)
    target: str = Field(max_length=50)
    payload: dict


class RulePayloadIn(BaseModel):
    payload: dict


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: str
    kind: str
    target: str
    payload: dict
    created_by: int
    created_at: datetime.datetime


class AppliedChangeOut(BaseModel):
    rule_id: int
    phase: str
    target: str
    field: str
    before: Any
    after: Any
    actor: str
    at: datetime.datetime


class SheetOut(BaseModel):
    rows: list[dict]
    edits: list[AppliedChangeOut]


class ParticipantOut(BaseModel):
    name: str
    club: str | None
    nationality: str | None
    disciplines: list[str]
    status: Literal["confirmed", "unconfirmed"]
