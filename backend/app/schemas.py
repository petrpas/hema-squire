import datetime
import decimal
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
    Currency,
    ExtraCategory,
    RefundState,
    RegistrationState,
    RequestState,
    Role,
    UnpaidListTreatment,
)

# an option answer is a size, a shirt cut, a meal choice — never prose
OPTION_VALUE_MAX_LENGTH = 100


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
    # EUR prices, filled only in local + EUR mode; authoritative, never
    # computed from fee/fee_early (design Decision 1)
    fee_eur: int | None = Field(default=None, ge=0)
    fee_early_eur: int | None = Field(default=None, ge=0)
    # optional schedule + ruleset reference; informational, never affect pricing
    schedule_when: str | None = Field(default=None, max_length=200)
    schedule_where: str | None = Field(default=None, max_length=300)
    ruleset_name: str | None = Field(default=None, max_length=100)
    ruleset_url: str | None = Field(default=None, max_length=500)


class DisciplineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    capacity: int
    fee: int | None
    fee_early: int | None
    fee_eur: int | None
    fee_early_eur: int | None
    schedule_when: str | None
    schedule_where: str | None
    ruleset_name: str | None
    ruleset_url: str | None


class ExtraItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: ExtraCategory
    price: int = Field(ge=0)
    # EUR price, filled only in local + EUR mode; authoritative, never
    # computed from `price` (design Decision 1)
    price_eur: int | None = Field(default=None, ge=0)
    max_qty: int = Field(default=1, ge=1)
    # optional descriptive fields; informational, never affect pricing
    schedule_when: str | None = Field(default=None, max_length=200)
    schedule_where: str | None = Field(default=None, max_length=300)
    remark: str | None = Field(default=None, max_length=500)
    # optional single option the fencer answers on selection; choices empty
    # means free text. Never affects pricing.
    option_label: str | None = Field(default=None, max_length=50)
    option_choices: list[str] = []

    @model_validator(mode="after")
    def _option_shape(self) -> ExtraItemIn:
        label = (self.option_label or "").strip()
        self.option_label = label or None
        seen: list[str] = []
        for choice in self.option_choices:
            trimmed = choice.strip()
            if trimmed and trimmed not in seen:
                if len(trimmed) > OPTION_VALUE_MAX_LENGTH:
                    raise ValueError("option choice too long")
                seen.append(trimmed)
        self.option_choices = seen
        if self.option_choices and self.option_label is None:
            raise ValueError("option choices require an option label")
        return self


class ExtraItemOut(ExtraItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


# discount scopes may target the implicit discipline category or any extra category
ScopeCategory = Literal[
    "discipline", "seminar", "rental", "afterparty", "merch", "other_action", "other_item"
]


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
    # the EUR amount of a fixed discount — a price decision like any other
    # (design Decision 1), filled only in local + EUR mode. A percentage
    # effect is currency-neutral and carries no second value.
    value_eur: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _percent_bounds(self) -> DiscountEffect:
        if self.kind == "percent" and self.value > 100:
            raise ValueError("percent discount cannot exceed 100")
        if self.kind == "percent" and self.value_eur is not None:
            raise ValueError("percent discount cannot carry a EUR amount")
        return self


class DiscountIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    condition: DiscountCondition
    effect: DiscountEffect
    scope: list[ScopeCategory] = ["discipline"]


class OrganizerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    link: str | None = Field(default=None, max_length=500)


class OrganizerOut(BaseModel):
    name: str
    link: str | None = None


def _tolerant_organizers(value: Any) -> Any:
    """Normalize bare-string organizer entries left by a partially-migrated
    or restored-from-old-export deployment into name+link dicts."""
    if not isinstance(value, list):
        return value
    return [{"name": entry, "link": None} if isinstance(entry, str) else entry for entry in value]


class TournamentCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")
    display_name: str = Field(min_length=1, max_length=200)
    date: datetime.date
    language: str = "cs"


class TournamentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=400)
    date: datetime.date | None = None
    language: str | None = None
    location: str | None = Field(default=None, max_length=300)
    description: str | None = None
    qualification_open: bool | None = None
    qualification_criteria: str | None = None
    registration_instructions: str | None = None
    local_currency: Currency | None = None
    eur_payments_enabled: bool | None = None
    # local-currency units per 1 EUR; a Setup convenience for recalculate-
    # missing only (design Decision 3) — a non-positive rate is meaningless
    eur_rate: decimal.Decimal | None = Field(default=None, gt=0)
    organizers: list[OrganizerIn] | None = None
    registration_opens: datetime.date | None = None
    registration_closes: datetime.date | None = None
    # unset means "same window as registration"; when both this and
    # registration_closes are set, this must not fall after it (router-checked)
    amendments_close: datetime.date | None = None
    discounts: list[DiscountIn] | None = None
    reservation_validity_days: int | None = Field(default=None, gt=0)
    reminder_day: int | None = Field(default=None, gt=0)
    amount_tolerance_percent: int | None = Field(default=None, ge=0, le=100)
    refundable_until: datetime.date | None = None
    bank_account: str | None = None
    # hours after expiry a VS-matched payment may still reinstate a
    # reservation, subject to capacity; 0 disables automatic reinstatement
    expiry_grace_hours: int | None = Field(default=None, ge=0)
    fio_token: str | None = None
    unpaid_list_treatment: UnpaidListTreatment | None = None
    output_sheet_url: str | None = None
    hr_category_map: dict[str, str] | None = None
    early_bird_until: datetime.date | None = None
    weapon_rental_fee: int | None = Field(default=None, ge=0)
    weapon_rental_fee_early: int | None = Field(default=None, ge=0)
    afterparty_fee: int | None = Field(default=None, ge=0)
    afterparty_fee_early: int | None = Field(default=None, ge=0)
    # editable only until the tournament's first registration (design
    # Decision 2); rejected otherwise, and rejected on collision
    vs_series: int | None = Field(default=None, ge=1, le=99)

    # a rate is a Setup convenience the organizer reads back, not a computed
    # figure; two decimal places is what an organizer actually types
    @field_validator("eur_rate")
    @classmethod
    def _quantize_rate(cls, value: decimal.Decimal | None) -> decimal.Decimal | None:
        if value is None:
            return None
        return value.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)


# the three currency modes a tournament can be in (design Decision 2):
# "local" — a single local currency; "local_eur" — local plus EUR as an
# accepted second currency; "eur" — the local currency is EUR itself, so
# there is no second currency, regardless of eur_payments_enabled
CurrencyMode = Literal["local", "local_eur", "eur"]


def currency_mode(local_currency: Currency, eur_payments_enabled: bool) -> CurrencyMode:
    if local_currency == Currency.EUR:
        return "eur"
    if eur_payments_enabled:
        return "local_eur"
    return "local"


class TournamentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    display_name: str
    subtitle: str | None
    has_logo: bool
    date: datetime.date
    language: str
    owner_id: int | None
    cancelled_at: datetime.datetime | None
    published_at: datetime.datetime | None
    reservation_validity_days: int
    reminder_day: int
    amount_tolerance_percent: int
    refundable_until: datetime.date | None
    bank_account: str | None
    expiry_grace_hours: int
    unpaid_list_treatment: UnpaidListTreatment
    output_sheet_url: str | None
    hr_category_map: dict[str, str]
    early_bird_until: datetime.date | None
    weapon_rental_fee: int
    weapon_rental_fee_early: int | None
    afterparty_fee: int
    afterparty_fee_early: int | None
    location: str | None
    description: str | None
    qualification_open: bool
    qualification_criteria: str | None
    registration_instructions: str | None
    local_currency: Currency
    eur_payments_enabled: bool
    eur_rate: decimal.Decimal | None
    organizers: list[OrganizerOut]
    registration_opens: datetime.date | None
    registration_closes: datetime.date | None
    amendments_close: datetime.date | None
    discounts: list[DiscountIn]
    extra_items: list[ExtraItemOut] = []
    # filled by the detail endpoint from setup.setup_missing(); None elsewhere
    setup_missing: list[str] | None = None
    # derived from local_currency + eur_payments_enabled; a convenience for
    # the frontend rather than a stored fact (design Decision 2)
    currency_mode: CurrencyMode = "local"
    disciplines: list[DisciplineOut]
    vs_year: int
    vs_series: int
    # YYNN every variable symbol this tournament issues starts with
    vs_prefix: int
    # False once the tournament has a first registration (design Decision 2);
    # filled explicitly by endpoints that know the answer, True elsewhere
    vs_series_editable: bool = True

    @field_validator("organizers", mode="before")
    @classmethod
    def _normalize_organizers(cls, value: Any) -> Any:
        return _tolerant_organizers(value)

    @model_validator(mode="after")
    def _derive_currency_mode(self) -> TournamentOut:
        self.currency_mode = currency_mode(self.local_currency, self.eur_payments_enabled)
        return self


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
    hr_shared: bool = False


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
    # answer to the item's option; presence is validated against the item at
    # registration time (the schema cannot see which item this points at)
    option_value: str | None = Field(default=None, max_length=OPTION_VALUE_MAX_LENGTH)


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
    option_label: str | None = None
    option_value: str | None = None


class RegistrationOut(BaseModel):
    state: RegistrationState
    vs: int
    total_amount: int
    # total_amount less what has been credited so far; the single figure the
    # fencer needs, never a total and a payment history to subtract by hand
    outstanding_amount: decimal.Decimal
    # the EUR pair, absent (not zero) when the tournament does not price in
    # EUR — both are stored figures, never derived from the local ones
    total_eur: int | None = None
    outstanding_eur_amount: decimal.Decimal | None = None
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


class DiscountBreakdownOut(BaseModel):
    name: str
    effect: DiscountEffect
    applied: bool
    # what the discount deducted, read from the computation that produced the
    # total alongside it — per currency for a fixed effect, local-only (design
    # Decision 3) for a currency-neutral percentage effect; both None when the
    # discount did not apply
    deducted: int | None = None
    deducted_eur: int | None = None


class PricePreviewOut(BaseModel):
    total: int
    currency: Currency = Currency.CZK
    # the stored EUR total, independently summed from EUR prices — omitted
    # (not derived) when the tournament does not price in EUR
    eur_total: int | None = None
    # one entry per discount the tournament configures, in configured order,
    # empty for a tournament that configures none
    discounts: list[DiscountBreakdownOut] = []


class PaymentInstructionsOut(BaseModel):
    amount: int
    currency: Currency = Currency.CZK
    iban: str
    vs: int
    message: str
    expires_at: datetime.datetime | None
    spayd: str
    qr_png_base64: str
    # the EUR pair is absent, not empty, when the tournament takes no EUR
    eur_amount: int | None = None
    eur_spayd: str | None = None
    eur_qr_png_base64: str | None = None


class OpenDisciplineOut(BaseModel):
    code: str
    name: str
    fee: int | None
    fee_eur: int | None = None
    taken: int
    capacity: int
    queue_length: int


RegistrationStatus = Literal["open", "opens_on", "closed"]
MyRegistrationState = Literal["none", "reserved", "paid", "substitute", "cancelled"]


class OpenTournamentOut(BaseModel):
    slug: str
    display_name: str
    subtitle: str | None = None
    has_logo: bool = False
    date: datetime.date
    location: str | None
    description: str | None = None
    qualification_open: bool = True
    qualification_criteria: str | None = None
    local_currency: Currency = Currency.CZK
    organizers: list[OrganizerOut]
    registration_status: RegistrationStatus
    registration_opens_on: datetime.date | None = None
    disciplines: list[OpenDisciplineOut]
    my_registration_state: MyRegistrationState

    @field_validator("organizers", mode="before")
    @classmethod
    def _normalize_organizers(cls, value: Any) -> Any:
        return _tolerant_organizers(value)


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
    user_identification: str | None
    comment: str | None
    specification: str | None
    specific_symbol: str | None
    status: str | None
    status_reason: str | None
    matched_registration_id: int | None
    # when the matcher last considered this transaction (design Decision 2)
    last_evaluated_at: datetime.datetime | None
    # only meaningful for a flagged transaction; whether reinstate is offered
    # (capacity re-checked at read time — see routers.payments._transaction_out)
    reinstate_available: bool = False
    # detected VS values that resolve to an issued registration; pre-fills
    # the manual link dialog for an unmatched transaction (design Decisions
    # 5 and 6) — filled by routers.payments._transaction_out
    candidate_vs: list[int] = []


class LinkIn(BaseModel):
    transaction_id: int
    vs: list[int] = Field(min_length=1)


class IngestAndMatchOut(BaseModel):
    new: int
    duplicate: int
    matched: int
    flagged: int
    unmatched: int
    # credited but short of the amount due; left reserved (design Decision 1)
    partial: int = 0
    # belonged to a sibling tournament on the same bank account; recorded, not
    # queued here (design Decision 5) — distinct from matched/flagged/unmatched
    set_aside: int


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
