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

from app import accounts, constraints, setup
from app.constraints import DEFAULT_TIMEZONE
from app.errors import FieldValueError
from app.fieldtypes import (
    DisciplineSlugStr,
    HttpUrlStr,
    MultilineStr,
    SingleLineStr,
    TolerantDecimal,
    TolerantInt,
)
from app.i18n import catalog
from app.models import (
    Currency,
    DisciplineKind,
    ExtraCategory,
    PaymentMode,
    RefundState,
    RegistrationState,
    RequestState,
    Role,
    UnpaidListTreatment,
)

# an option answer is a size, a shirt cut, a meal choice — never prose
OPTION_VALUE_MAX_LENGTH = constraints.OPTION_VALUE_MAX_LENGTH


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=constraints.PASSWORD_MIN_LENGTH)
    display_name: (
        SingleLineStr(
            constraints.DISPLAY_NAME_MAX_LENGTH, min_length=constraints.DISPLAY_NAME_MIN_LENGTH
        )
        | None
    ) = None
    hr_id: int | None = None
    club: SingleLineStr(constraints.CLUB_MAX_LENGTH) | None = None
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
    message: MultilineStr(constraints.PLEA_MESSAGE_MAX_LENGTH) | None = None


class PleaOut(BaseModel):
    """The account's own latest plea; state is None when it has never pled."""

    state: RequestState | None
    message: str | None
    created_at: datetime.datetime | None
    decided_at: datetime.datetime | None


class AccountUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: (
        SingleLineStr(
            constraints.DISPLAY_NAME_MAX_LENGTH, min_length=constraints.DISPLAY_NAME_MIN_LENGTH
        )
        | None
    ) = None
    club: SingleLineStr(constraints.CLUB_MAX_LENGTH) | None = None
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
    # optional on creation: the system generates one from the classification
    # when omitted (design discipline-identity D3); an organizer override is
    # checked for uniqueness by the router, which is where a conflict can be
    # named against the tournament's other disciplines. Normalized ahead of
    # its own pattern (design add-field-validation D6) — see fieldtypes.py.
    slug: DisciplineSlugStr() = None
    name: SingleLineStr(constraints.DISCIPLINE_NAME_MAX_LENGTH) | None = None
    # display order among the tournament's disciplines; omitted means "leave
    # the current position alone" on update, "append at the end" on create
    # (the ORM column default), since most callers never touch ordering
    ordinal: int | None = None
    # the five taxonomy weapons are offered as suggestions, but any weapon is
    # accepted (design discipline-identity D4); gender and material stay
    # closed sets
    weapon: SingleLineStr(
        constraints.DISCIPLINE_WEAPON_MAX_LENGTH,
        min_length=constraints.DISCIPLINE_WEAPON_MIN_LENGTH,
    )
    gender: Literal["", "W", "M"] = ""
    material: Literal["", "Plastic"] = ""
    # individual is the default and behaves exactly as before team disciplines
    # existed; a team discipline's capacity counts teams and its fee is per
    # team (design team-disciplines D2)
    kind: DisciplineKind = DisciplineKind.INDIVIDUAL
    team_min: int | None = Field(default=None, ge=constraints.TEAM_BOUND_MIN)
    team_max: int | None = Field(default=None, ge=constraints.TEAM_BOUND_MIN)
    capacity: TolerantInt = Field(gt=0)
    # local-currency money: non-negative, ceiling resolved per request from
    # the tournament's local_currency (design D4/2.4a) — the router checks it,
    # since a static Field bound cannot know which currency this carries
    fee: TolerantInt | None = Field(default=None, ge=0)
    fee_early: TolerantInt | None = Field(default=None, ge=0)
    # EUR prices, filled only in local + EUR mode; authoritative, never
    # computed from fee/fee_early (design Decision 1) — always EUR, so the
    # ceiling is static
    fee_eur: TolerantInt | None = Field(default=None, ge=0, le=constraints.MONEY_MAX["EUR"])
    fee_early_eur: TolerantInt | None = Field(default=None, ge=0, le=constraints.MONEY_MAX["EUR"])
    # optional schedule + ruleset reference; informational, never affect pricing
    schedule_when: SingleLineStr(constraints.DISCIPLINE_SCHEDULE_WHEN_MAX_LENGTH) | None = None
    schedule_where: SingleLineStr(constraints.DISCIPLINE_SCHEDULE_WHERE_MAX_LENGTH) | None = None
    ruleset_name: SingleLineStr(constraints.DISCIPLINE_RULESET_NAME_MAX_LENGTH) | None = None
    ruleset_url: HttpUrlStr(constraints.DISCIPLINE_RULESET_URL_MAX_LENGTH) | None = None

    @model_validator(mode="after")
    def _team_bounds(self) -> DisciplineIn:
        if self.kind == DisciplineKind.TEAM:
            if self.team_min is None or self.team_max is None:
                raise ValueError("team discipline requires team_min and team_max")
            if self.team_max < self.team_min:
                raise ValueError("team_max must not be below team_min")
        elif self.team_min is not None or self.team_max is not None:
            raise ValueError("team_min/team_max are only valid for a team discipline")
        return self

    @model_validator(mode="after")
    def _capacity_ceiling(self) -> DisciplineIn:
        # a team discipline's capacity counts teams, an individual's counts
        # fencers — the ceiling is resolved from `kind`, not a static bound
        # (design add-field-validation)
        ceiling = constraints.DISCIPLINE_CAPACITY_MAX[str(self.kind)]
        if self.capacity > ceiling:
            raise FieldValueError("capacity", "out_of_range", {"min": 1, "max": ceiling})
        return self


class DisciplineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    ordinal: int
    weapon: str
    gender: str
    material: str
    kind: DisciplineKind
    team_min: int | None
    team_max: int | None
    capacity: int
    fee: int | None
    fee_early: int | None
    fee_eur: int | None
    fee_early_eur: int | None
    schedule_when: str | None
    schedule_where: str | None
    ruleset_name: str | None
    ruleset_url: str | None
    # not an ORM attribute; filled explicitly by every construction site from
    # a per-tournament grouped query (design discipline-identity-modal D6) —
    # never inferred from availability.taken_seats, which excludes cancelled
    # and expired entries, substitutes, and teams entirely
    identity_frozen: bool = False


class ExtraItemIn(BaseModel):
    name: SingleLineStr(
        constraints.EXTRA_ITEM_NAME_MAX_LENGTH, min_length=constraints.EXTRA_ITEM_NAME_MIN_LENGTH
    )
    category: ExtraCategory
    # local-currency money: ceiling resolved per request (design 2.4a)
    price: TolerantInt = Field(ge=0)
    # EUR price, filled only in local + EUR mode; authoritative, never
    # computed from `price` (design Decision 1) — always EUR, static ceiling
    price_eur: TolerantInt | None = Field(default=None, ge=0, le=constraints.MONEY_MAX["EUR"])
    max_qty: TolerantInt = Field(default=1, ge=constraints.EXTRA_ITEM_MAX_QTY_MIN)
    # optional descriptive fields; informational, never affect pricing
    schedule_when: SingleLineStr(constraints.EXTRA_ITEM_SCHEDULE_WHEN_MAX_LENGTH) | None = None
    schedule_where: SingleLineStr(constraints.EXTRA_ITEM_SCHEDULE_WHERE_MAX_LENGTH) | None = None
    remark: MultilineStr(constraints.EXTRA_ITEM_REMARK_MAX_LENGTH) | None = None
    # optional single option the fencer answers on selection; choices empty
    # means free text. Never affects pricing.
    option_label: SingleLineStr(constraints.EXTRA_ITEM_OPTION_LABEL_MAX_LENGTH) | None = None
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
                    raise ValueError("too_long")
                seen.append(trimmed)
        self.option_choices = seen
        if self.option_choices and self.option_label is None:
            raise ValueError("option choices require an option label")
        return self

    @model_validator(mode="after")
    def _max_qty_ceiling(self) -> ExtraItemIn:
        # action categories (seminar/afterparty/other_action) are always
        # forced to 1 by the router regardless of what is submitted, so they
        # carry no ceiling of their own here (design add-field-validation)
        ceiling = constraints.EXTRA_ITEM_MAX_QTY_CEILING.get(str(self.category))
        if ceiling is not None and self.max_qty > ceiling:
            raise FieldValueError(
                "max_qty",
                "out_of_range",
                {"min": constraints.EXTRA_ITEM_MAX_QTY_MIN, "max": ceiling},
            )
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
    count: int | None = Field(default=None, ge=constraints.DISCOUNT_COUNT_MIN)
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
    # a fixed amount is local-currency money, ceiling resolved per request
    # (design 2.4a); a percent effect is bounded to 0-100 below
    value: TolerantInt = Field(ge=0)
    # the EUR amount of a fixed discount — a price decision like any other
    # (design Decision 1), filled only in local + EUR mode. A percentage
    # effect is currency-neutral and carries no second value. Always EUR, so
    # the ceiling is static.
    value_eur: TolerantInt | None = Field(default=None, ge=0, le=constraints.MONEY_MAX["EUR"])

    @model_validator(mode="after")
    def _percent_bounds(self) -> DiscountEffect:
        if self.kind == "percent" and self.value > constraints.PERCENT_MAX:
            raise ValueError("out_of_range")
        if self.kind == "percent" and self.value_eur is not None:
            raise ValueError("percent discount cannot carry a EUR amount")
        return self


class DiscountIn(BaseModel):
    name: SingleLineStr(
        constraints.DISCOUNT_NAME_MAX_LENGTH, min_length=constraints.DISCOUNT_NAME_MIN_LENGTH
    )
    condition: DiscountCondition
    effect: DiscountEffect
    scope: list[ScopeCategory] = ["discipline"]


class OrganizerIn(BaseModel):
    name: SingleLineStr(
        constraints.ORGANIZER_NAME_MAX_LENGTH, min_length=constraints.ORGANIZER_NAME_MIN_LENGTH
    )
    link: HttpUrlStr(constraints.ORGANIZER_LINK_MAX_LENGTH) | None = None


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
    slug: str = Field(pattern=constraints.TOURNAMENT_SLUG_PATTERN)
    display_name: SingleLineStr(
        constraints.TOURNAMENT_DISPLAY_NAME_MAX_LENGTH,
        min_length=constraints.TOURNAMENT_DISPLAY_NAME_MIN_LENGTH,
    )
    date: datetime.date
    language: str = "cs"


class TournamentUpdate(BaseModel):
    display_name: (
        SingleLineStr(
            constraints.TOURNAMENT_DISPLAY_NAME_MAX_LENGTH,
            min_length=constraints.TOURNAMENT_DISPLAY_NAME_MIN_LENGTH,
        )
        | None
    ) = None
    subtitle: SingleLineStr(constraints.TOURNAMENT_SUBTITLE_MAX_LENGTH) | None = None
    date: datetime.date | None = None
    language: str | None = None
    location: SingleLineStr(constraints.TOURNAMENT_LOCATION_MAX_LENGTH) | None = None
    description: MultilineStr(constraints.TOURNAMENT_DESCRIPTION_MAX_LENGTH) | None = None
    qualification_open: bool | None = None
    qualification_criteria: (
        MultilineStr(constraints.TOURNAMENT_QUALIFICATION_CRITERIA_MAX_LENGTH) | None
    ) = None
    registration_instructions: (
        MultilineStr(constraints.TOURNAMENT_REGISTRATION_INSTRUCTIONS_MAX_LENGTH) | None
    ) = None
    local_currency: Currency | None = None
    eur_payments_enabled: bool | None = None
    # local-currency units per 1 EUR; a Setup convenience for recalculate-
    # missing only (design Decision 3) — a non-positive rate is meaningless
    eur_rate: TolerantDecimal | None = Field(default=None, gt=0)
    organizers: list[OrganizerIn] | None = None
    registration_opens: datetime.date | None = None
    # the wall clock registration opens on `registration_opens`, in the
    # tournament's `timezone`. A child of the date: clearing the date clears
    # it, and one sent without a date is refused (router-checked), as is one
    # the zone skips on that day (design add-registration-open-time D4, D9)
    registration_opens_time: datetime.time | None = None
    # the tournament's own local zone as an IANA identifier; every date on the
    # timeline is read as a day in it. Validity is decided by the zone
    # database, not by the length (router-checked)
    timezone: str | None = Field(
        default=None, max_length=constraints.TOURNAMENT_TIMEZONE_MAX_LENGTH
    )
    registration_closes: datetime.date | None = None
    # unset means "same window as registration"; when both this and
    # registration_closes are set, this must not fall after it (router-checked)
    amendments_close: datetime.date | None = None
    # meaningful only when the tournament offers a team discipline; checks,
    # never enforces, and is deliberately independent of registration_closes
    # and amendments_close in both directions (design team-disciplines D7) —
    # validated only as a date on or before the tournament date (router-checked)
    team_composition_deadline: datetime.date | None = None
    discounts: list[DiscountIn] | None = None
    # how a seat is held until the seating deadline; unset leaves the stored
    # mode alone, and a tournament that never chose one is `immediate`
    payment_mode: PaymentMode | None = None
    # the date seating settles: a soft boundary inside registration_closes,
    # not the hard close. Unset it resolves to registration_closes
    # (setup.seating_deadline_for); must not fall after it (router-checked)
    seating_deadline: datetime.date | None = None
    # flat deposit owed at registration in deposit mode, local-currency money
    # with its independent EUR counterpart; required and positive in that mode,
    # ignored in the others (router-checked)
    deposit_amount: TolerantInt | None = Field(default=None, ge=0)
    deposit_amount_eur: TolerantInt | None = Field(default=None, ge=0)
    reservation_validity_days: int | None = Field(
        default=None,
        ge=constraints.RESERVATION_VALIDITY_DAYS_MIN,
        le=constraints.RESERVATION_VALIDITY_DAYS_MAX,
    )
    reminder_day: int | None = Field(default=None, gt=0)
    amount_tolerance_percent: int | None = Field(default=None, ge=0, le=constraints.PERCENT_MAX)
    refundable_until: datetime.date | None = None
    bank_account: (
        SingleLineStr(
            constraints.TOURNAMENT_BANK_ACCOUNT_MAX_LENGTH, pattern=constraints.BANK_ACCOUNT_PATTERN
        )
        | None
    ) = None
    # hours after expiry a VS-matched payment may still reinstate a
    # reservation, subject to capacity; 0 disables automatic reinstatement
    expiry_grace_hours: int | None = Field(default=None, ge=0)
    fio_token: SingleLineStr(constraints.TOURNAMENT_FIO_TOKEN_MAX_LENGTH) | None = None
    unpaid_list_treatment: UnpaidListTreatment | None = None
    output_sheet_url: HttpUrlStr(constraints.TOURNAMENT_OUTPUT_SHEET_URL_MAX_LENGTH) | None = None
    hr_category_map: (
        dict[
            SingleLineStr(constraints.HR_CATEGORY_MAP_KEY_MAX_LENGTH),
            SingleLineStr(constraints.HR_CATEGORY_MAP_VALUE_MAX_LENGTH),
        ]
        | None
    ) = None
    early_bird_until: datetime.date | None = None
    # local-currency money: ceiling resolved per request (design 2.4a); no
    # EUR-suffixed counterpart exists for these two legacy fixed fees, which
    # is why a tournament using them cannot enable EUR (_apply_currency_invariants)
    weapon_rental_fee: TolerantInt | None = Field(default=None, ge=0)
    weapon_rental_fee_early: TolerantInt | None = Field(default=None, ge=0)
    afterparty_fee: TolerantInt | None = Field(default=None, ge=0)
    afterparty_fee_early: TolerantInt | None = Field(default=None, ge=0)
    # editable only until the tournament's first registration (design
    # Decision 2); rejected otherwise, and rejected on collision
    vs_series: int | None = Field(
        default=None, ge=constraints.VS_SERIES_MIN, le=constraints.VS_SERIES_MAX
    )

    # a rate is a Setup convenience the organizer reads back, not a computed
    # figure; two decimal places is what an organizer actually types
    @field_validator("eur_rate")
    @classmethod
    def _quantize_rate(cls, value: decimal.Decimal | None) -> decimal.Decimal | None:
        if value is None:
            return None
        return value.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

    # accepts either form and stores the canonical IBAN (design Decision 1);
    # runs after SingleLineStr's length/shape bound, which only catches
    # something that is not plausibly an account at all
    @field_validator("bank_account")
    @classmethod
    def _normalize_bank_account(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return accounts.parse(value)


class TournamentModeIn(BaseModel):
    """The tournament's mode, chosen as a whole. All four features are given
    together and none is optional: a mode is a shape the organizer picks, not
    four settings toggled one at a time, so a request that omits a feature is
    asking for it to be off rather than to be left alone. Easy mode is all
    four false (design tournament-modes D2)."""

    feature_schedule: bool
    feature_payments: bool
    feature_teams: bool
    feature_extras: bool


class TournamentModeOut(TournamentModeIn):
    """What the mode dialog opens on. Deliberately the request model read back,
    so the two can never describe different sets of features."""

    model_config = ConfigDict(from_attributes=True)


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
    payment_mode: PaymentMode
    seating_deadline: datetime.date | None
    seating_settled_at: datetime.datetime | None
    deposit_amount: int | None
    deposit_amount_eur: int | None
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
    registration_opens_time: datetime.time | None
    timezone: str
    registration_closes: datetime.date | None
    amendments_close: datetime.date | None
    team_composition_deadline: datetime.date | None
    # the tournament's mode: easy mode is all four off (design
    # tournament-modes D2). Read by the console to decide which tabs, sections
    # and phases it offers, and by the fencer-facing surfaces to decide
    # whether money is being asked for at all
    feature_schedule: bool
    feature_payments: bool
    feature_teams: bool
    feature_extras: bool
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
    # the moment registration opens, resolved from the three fields above so
    # that no consumer has to know this zone's daylight-saving rules to display
    # it or to compare against it (design add-registration-open-time D6).
    # Derived, never stored and never accepted on a write
    registration_opens_at: datetime.datetime | None = None
    # this response's own instant. What lets a client measure its clock against
    # the system's, rather than counting down on a clock that may be wrong (D6)
    server_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @field_validator("organizers", mode="before")
    @classmethod
    def _normalize_organizers(cls, value: Any) -> Any:
        return _tolerant_organizers(value)

    @model_validator(mode="after")
    def _derive_currency_mode(self) -> TournamentOut:
        self.currency_mode = currency_mode(self.local_currency, self.eur_payments_enabled)
        return self

    @model_validator(mode="after")
    def _resolve_opening_instant(self) -> TournamentOut:
        # folded here rather than by each endpoint, so every response carrying
        # the parts carries the resolved moment with them
        self.registration_opens_at = setup.opening_instant(
            self.registration_opens, self.registration_opens_time, self.timezone
        )
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


class TeamEntryIn(BaseModel):
    """One team named on a registration or an amendment. `id`, when it matches
    an existing team of this registration, keeps that team's roster and only
    updates its name/discipline; omitted or non-matching, the team (re)starts
    with an empty roster (design team-disciplines D1, task 4.3). Ignored
    entirely on an initial registration, which has no existing teams."""

    id: int | None = None
    slug: str
    # SingleLineStr trims and collapses whitespace before min_length is
    # checked, so a whitespace-only name is already rejected as too_short
    name: SingleLineStr(
        constraints.TEAM_NAME_MAX_LENGTH, min_length=constraints.TEAM_NAME_MIN_LENGTH
    )


class PreviewTeamIn(BaseModel):
    """A team entry for the price preview: identified by its discipline alone
    — a team's name and roster are not pricing inputs (spec: Price preview)."""

    slug: str


class RosterMemberIn(BaseModel):
    name: SingleLineStr(
        constraints.ROSTER_MEMBER_NAME_MAX_LENGTH,
        min_length=constraints.ROSTER_MEMBER_NAME_MIN_LENGTH,
    )
    hr_id: int | None = None
    club: SingleLineStr(constraints.ROSTER_MEMBER_CLUB_MAX_LENGTH) | None = None
    nationality: SingleLineStr(constraints.ROSTER_MEMBER_NATIONALITY_MAX_LENGTH) | None = None


class RosterMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    hr_id: int | None
    club: str | None
    nationality: str | None


class RosterUpdateIn(BaseModel):
    members: list[RosterMemberIn] = []


class TeamEntryOut(BaseModel):
    id: int
    slug: str
    name: str
    waitlisted: bool
    # per-team fee, in each configured currency — never multiplied by roster
    # size (design team-disciplines D2)
    fee: int
    fee_eur: int | None = None
    team_min: int
    team_max: int
    members: list[RosterMemberOut] = []
    # the entering fencer's own name/HR binding, suggested as the first member
    # while the roster is still empty; a UI convenience only, never persisted
    # as a role (design team-disciplines D5) — None once any member exists
    prefill: RosterMemberOut | None = None


class ExtraSelectionIn(BaseModel):
    extra_item_id: int
    qty: TolerantInt = Field(default=1, ge=constraints.EXTRA_SELECTION_QTY_MIN)
    # answer to the item's option; presence is validated against the item at
    # registration time (the schema cannot see which item this points at)
    option_value: SingleLineStr(OPTION_VALUE_MAX_LENGTH) | None = None


class RegisterIn(BaseModel):
    # at least one discipline OR one team must be selected; enforced in the
    # router, where both fields are visible together (a team-only registration
    # is valid — spec: "Registration consisting only of a team")
    disciplines: list[str] = []
    weapon_rentals: list[str] = []
    afterparty: bool = False
    aftersparring: bool = False
    accommodation: str | None = None
    notes: str | None = None
    extras: list[ExtraSelectionIn] = []
    teams: list[TeamEntryIn] = []


class RegistrationEntryOut(BaseModel):
    slug: str
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
    teams: list[TeamEntryOut] = []


class AvailabilityOut(BaseModel):
    slug: str
    kind: DisciplineKind = DisciplineKind.INDIVIDUAL
    capacity: int
    taken: int
    free: int
    queue_length: int
    # roster bounds, present only for a team-kind row (design team-disciplines
    # 4.8); absent for an individual discipline
    team_min: int | None = None
    team_max: int | None = None


class PricePreviewIn(BaseModel):
    # at least one discipline or team must be selected; enforced in the router
    # (a team-only preview is valid — spec: "Team previewed without a roster")
    disciplines: list[str] = []
    weapon_rentals: list[str] = []
    afterparty: bool = False
    extras: list[ExtraSelectionIn] = []
    teams: list[PreviewTeamIn] = []


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
    # the domestic form for a Czech account, so a Czech payer is not made to
    # read an IBAN; absent for any other country (design
    # accept-czech-account-format Decision 2)
    account_domestic: str | None = None
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
    # not rendered to fencers (design discipline-identity D6); carried only as
    # a stable list key
    slug: str
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
    # the opening *day*, kept as it was so a client written before the opening
    # moment existed still reads this list
    registration_opens_on: datetime.date | None = None
    # the opening *moment*: resolved, absolute, offset-bearing (design
    # add-registration-open-time D6). Set only while the status is opens_on
    registration_opens_at: datetime.datetime | None = None
    # the zone the opening hour is stated in, so a consumer can name it
    timezone: str = DEFAULT_TIMEZONE
    # this response's own instant, for the same reason as on TournamentOut
    server_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    disciplines: list[OpenDisciplineOut]
    my_registration_state: MyRegistrationState
    # the caller's other bond to the tournament: owner or console team member.
    # Independent of my_registration_state — an entry may carry both.
    organized: bool = False

    @field_validator("organizers", mode="before")
    @classmethod
    def _normalize_organizers(cls, value: Any) -> Any:
        return _tolerant_organizers(value)


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
    vs: list[int] = Field(min_length=constraints.LINK_VS_MIN_ITEMS)


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
    phase: str = Field(max_length=constraints.RULE_PHASE_MAX_LENGTH)
    kind: str = Field(max_length=constraints.RULE_KIND_MAX_LENGTH)
    target: str = Field(max_length=constraints.RULE_TARGET_MAX_LENGTH)
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


class ConsoleTeamOut(BaseModel):
    """One team as the organizer's read-only teams view presents it (spec:
    "Organizer's read-only teams view"). Offers no action — no admission, no
    roster editing on the entrant's behalf, no cancellation; the console
    renders none for a reason, since those controls do not exist here."""

    id: int
    name: str
    entering_fencer: str
    waitlisted: bool
    # position in the team waitlist, in entry order; None for a placed team
    waitlist_position: int | None = None
    members: list[RosterMemberOut] = []
    # distinguishes a team whose roster is short after the deadline has
    # passed (deadline set, in the past, and members below team_min);
    # unrelated to waitlisted, and never true with no deadline configured
    below_minimum: bool


class ConsoleTeamDisciplineOut(BaseModel):
    slug: str
    name: str
    team_min: int
    team_max: int
    teams: list[ConsoleTeamOut] = []


class QueueEntryOut(BaseModel):
    """One fencer's placement in one individual discipline, above or below the
    line, as the organizer's queue view presents it."""

    registration_id: int
    fencer: str
    club: str | None
    vs: int | None
    registered_at: datetime.datetime
    # place in the substitute queue by registration time; None when seated
    queue_position: int | None = None


class QueueDisciplineOut(BaseModel):
    slug: str
    name: str
    capacity: int
    taken: int
    free: int
    seated: list[QueueEntryOut] = []
    queued: list[QueueEntryOut] = []


class QueueOut(BaseModel):
    """The seating picture for the whole tournament: where the line falls in
    every individual discipline, and whether it has been drawn yet."""

    # the resolved deadline, falling back to registration close and then the
    # tournament date (setup.seating_deadline_for) — never the raw column
    seating_deadline: datetime.date
    seating_settled_at: datetime.datetime | None
    # how many registrations settling now would move below the line; what the
    # console states before asking to confirm an irreversible settlement
    pending_demotions: int
    disciplines: list[QueueDisciplineOut] = []


class SettleSeatingOut(BaseModel):
    demoted: int
    seating_settled_at: datetime.datetime


class ParticipantOut(BaseModel):
    name: str
    club: str | None
    nationality: str | None
    disciplines: list[str]
    status: Literal["confirmed", "unconfirmed"]
