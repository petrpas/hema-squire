"""Core multi-tenant data model.

Money amounts are whole units of the tournament's local currency, stored as
integers. A tournament that also accepts EUR stores a second, independent
whole-unit EUR figure alongside each local one — never derived from it.
Fencer accounts are global; everything else is tournament-scoped.
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import taxonomy
from app.db import Base


class Role(enum.StrEnum):
    """Global role ladder; capabilities are rank-based (see app.auth). The
    deployment Owner is not a role — it is computed from settings.owner_email."""

    FENCER = "fencer"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class RequestState(enum.StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"


class UnpaidListTreatment(enum.StrEnum):
    HIDDEN = "hidden"
    GREYED = "greyed"


class Currency(enum.StrEnum):
    """A tournament's local currency — the unit every configured price and
    computed total is expressed in. Closed enum so widening it stays a code
    change; EUR is singled out because it is the one currency a tournament may
    additionally price and accept alongside its local currency (see
    Tournament.eur_payments_enabled) — never derived from it."""

    CZK = "CZK"
    EUR = "EUR"


class RegistrationState(enum.StrEnum):
    RESERVED = "reserved"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentMode(enum.StrEnum):
    """How a tournament's seat is held until the seating deadline.

    `immediate` is the behaviour every tournament had before the mode existed —
    the full amount is owed at registration and an unpaid reservation expires
    when its payment window closes — so it is the default and the value every
    pre-mode tournament carries.

    `deposit` holds the seat with a flat deposit: the deposit opens a payment
    window, crediting it closes that window (app.matching), and the balance is
    owed by the seating deadline. `reservation` holds the seat with nothing at
    all: no money is owed and no payment window opens until the seating
    deadline, by which the full amount is due.
    """

    IMMEDIATE = "immediate"
    DEPOSIT = "deposit"
    RESERVATION = "reservation"


class DisciplineKind(enum.StrEnum):
    """Whether a discipline is entered by one fencer or by a team (design
    team-disciplines D1). Frozen once any registration references it."""

    INDIVIDUAL = "individual"
    TEAM = "team"


class RefundState(enum.StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    REFUNDED = "refunded"


class ExtraCategory(enum.StrEnum):
    """Categories of billable extra items; discount scopes reference these
    (plus the implicit "discipline" category), so they form a closed enum.

    Divides into "action" categories (SEMINAR, AFTERPARTY, OTHER_ACTION —
    happen at a time and place) and "item" categories (RENTAL, MERCH,
    OTHER_ITEM — goods); see ACTION_CATEGORIES below."""

    SEMINAR = "seminar"
    RENTAL = "rental"
    AFTERPARTY = "afterparty"
    MERCH = "merch"
    OTHER_ACTION = "other_action"
    OTHER_ITEM = "other_item"


# action categories offer `when`/`where` and no quantity limit (stored as 1);
# item categories offer a quantity limit and no `when`/`where` (design D4)
ACTION_CATEGORIES = frozenset(
    {ExtraCategory.SEMINAR, ExtraCategory.AFTERPARTY, ExtraCategory.OTHER_ACTION}
)


def str_enum(enum_cls: type[enum.StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
        length=30,
    )


class Fencer(Base):
    """Global, portable fencer account, ideally bound to a HEMA Ratings profile."""

    __tablename__ = "fencers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(200))
    hr_id: Mapped[int | None] = mapped_column(index=True)
    nationality: Mapped[str | None] = mapped_column(String(100))
    club: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="cs")
    role: Mapped[Role] = mapped_column(str_enum(Role), default=Role.FENCER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    registrations: Mapped[list[Registration]] = relationship(back_populates="fencer")


class FencerProfileAudit(Base):
    """Audit trail of fencer profile changes (spec: profile changes are audited)."""

    __tablename__ = "fencer_profile_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    fencer_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    field: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (UniqueConstraint("vs_year", "vs_series"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    # optional free-text subtitle; may be longer than display_name, often empty
    subtitle: Mapped[str | None] = mapped_column(String(400))
    # optional logo stored inline (bounded/re-encoded on upload — see the logo
    # endpoints); kept in the DB so the deployment stays a single SQLite file.
    # Deferred so list queries never drag the blob; presence is read from the
    # always-loaded logo_mime via has_logo.
    logo_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    logo_mime: Mapped[str | None] = mapped_column(String(100))
    date: Mapped[date]
    # the single Tournament Owner (creator, until transferred); nullable only
    # for pre-role tournaments that had no organizers to backfill from
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("fencers.id"))
    # set when the Tournament Owner cancels; a cancelled tournament is hidden
    # from public listings and rejects new registrations, data retained
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # null means draft: invisible to fencers, closed to registration, freely
    # editable into incompleteness. Publication is one-way — no action ever
    # clears this (design D1 of add-explicit-publishing)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_id: Mapped[int | None] = mapped_column(ForeignKey("fencers.id"))
    language: Mapped[str] = mapped_column(String(10), default="cs")
    location: Mapped[str | None] = mapped_column(String(300))
    # optional free-form plain text, presented with line breaks preserved;
    # never interpreted as markup
    description: Mapped[str | None] = mapped_column(Text)
    # informational only; never gates registration (design D7)
    qualification_open: Mapped[bool] = mapped_column(default=True)
    qualification_criteria: Mapped[str | None] = mapped_column(Text)
    # optional plain text shown only on the registration form — the place for
    # registration/payment notes that do not belong on the public info screen
    registration_instructions: Mapped[str | None] = mapped_column(Text)
    # public-facing titular organizers (clubs/entities), each {"name", "link"};
    # independent of the account-based console access in TournamentOrganizer.
    # Entries may still be bare strings from a partially-migrated or
    # restored-from-old-export deployment; read via organizers_list().
    organizers: Mapped[list] = mapped_column(JSON, default=list)
    registration_opens: Mapped[date | None]
    registration_closes: Mapped[date | None]
    # freezes the roster for amendments independently of registration close;
    # unset means "same window as registration" (setup.amendment_availability)
    amendments_close: Mapped[date | None]
    # the date by which team rosters are expected to reach their disciplines'
    # minimum size; meaningful only when a team discipline exists. Checks, it
    # never enforces — no roster is locked, no team is cancelled or waitlisted,
    # and no capacity is freed on account of it (design team-disciplines D7)
    team_composition_deadline: Mapped[date | None]

    # payment and reservation parameters
    # how a seat is held (see PaymentMode); `immediate` is what every
    # tournament created before the mode existed does, so it is the default
    payment_mode: Mapped[PaymentMode] = mapped_column(
        str_enum(PaymentMode), default=PaymentMode.IMMEDIATE
    )
    # the date the tournament's seating settles: after it, registration is
    # still accepted but grants only a queue position, and money still owed on
    # a seated registration is overdue. Optional — unset it resolves to
    # registration_closes, which itself resolves to `date`
    # (setup.seating_deadline_for), mirroring amendments_close
    seating_deadline: Mapped[date | None]
    # flat deposit owed at registration in `deposit` mode, in whole units of
    # local_currency, with the independent EUR figure alongside it like every
    # other price. Never a percentage: a percentage would move when a
    # registration is amended, after it had already been paid (design D4)
    deposit_amount: Mapped[int | None]
    deposit_amount_eur: Mapped[int | None]
    # set by the settlement pass, by the deadline tick or by the organizer
    # settling early. Settlement is one-shot: its predicate is "reserved and
    # seated", which is exactly what admit_substitute produces, so without
    # this stamp every later tick would demote the fencers the organizer had
    # just promoted (design D6)
    seating_settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reservation_validity_days: Mapped[int] = mapped_column(default=10)
    reminder_day: Mapped[int] = mapped_column(default=5)
    amount_tolerance_percent: Mapped[int] = mapped_column(default=5)
    refundable_until: Mapped[date | None]
    bank_account: Mapped[str | None] = mapped_column(String(50))
    # how long after expiry a VS-matched payment may still reinstate a
    # reservation, subject to capacity (matching.py); 0 disables automatic
    # reinstatement and routes every post-expiry payment to organizer action
    expiry_grace_hours: Mapped[int] = mapped_column(default=48)
    unpaid_list_treatment: Mapped[UnpaidListTreatment] = mapped_column(
        str_enum(UnpaidListTreatment), default=UnpaidListTreatment.GREYED
    )

    # variable-symbol series: the YY and NN of every VS this tournament issues
    # (design Decision 1). The prefix is documentation only — matching never
    # parses it to pick a tournament, it only resolves the whole VS value
    # (design Decision 4). vs_next_seq is the next `nnn` to allocate.
    vs_year: Mapped[int]
    vs_series: Mapped[int]
    vs_next_seq: Mapped[int] = mapped_column(default=1)

    # currency: every configured price and every computed total is in whole
    # units of local_currency. When eur_payments_enabled and local_currency is
    # not already EUR, every priced thing additionally carries an independent,
    # organizer-typed EUR price (Discipline.fee_eur etc.) — never derived from
    # the local one. eur_rate is a Setup convenience only: local-currency units
    # per 1 EUR, read by exactly one thing, the recalculate-missing action that
    # fills empty price fields from filled ones. It is read by no pricing,
    # matching, email, or QR path — see pricing.selection_total and
    # matching.match_new_transactions, neither of which consults it.
    local_currency: Mapped[Currency] = mapped_column(
        str_enum(Currency), default=Currency.CZK
    )
    eur_payments_enabled: Mapped[bool] = mapped_column(default=False)
    # 2 decimal places — what an organizer actually types, not a computed
    # figure needing extra precision (schemas.TournamentUpdate quantizes on write)
    eur_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    fio_token: Mapped[str | None] = mapped_column(String(200))
    output_sheet_url: Mapped[str | None] = mapped_column(String(300))
    # taxonomy code (design discipline-identity D5) -> HR category keyword,
    # overriding the built-in default. Keyed by classification, not by
    # discipline identity, so disciplines sharing a classification (tiers)
    # share one entry and cannot drift apart.
    hr_category_map: Mapped[dict] = mapped_column(JSON, default=dict)

    # legacy billable extras; early-bird prices apply within the optional
    # window. Kept for pre-itemized tournaments so their totals stay
    # reproducible; tournaments with extra_items/discounts ignore these.
    early_bird_until: Mapped[date | None]
    weapon_rental_fee: Mapped[int] = mapped_column(default=0)
    weapon_rental_fee_early: Mapped[int | None]
    afterparty_fee: Mapped[int] = mapped_column(default=0)
    afterparty_fee_early: Mapped[int | None]

    # ordered pricing discounts: [{name, condition, effect, scope}], where a
    # `fixed` effect is {kind, value, value_eur} — value_eur is the EUR amount,
    # an independent organizer decision like every other EUR price, present
    # only in local + EUR mode; a `percent` effect is currency-neutral and
    # carries only {kind, value}. Shape is validated in schemas and
    # interpreted in pricing.py
    discounts: Mapped[list] = mapped_column(JSON, default=list)

    @property
    def has_logo(self) -> bool:
        # reads the always-loaded mime, never the deferred blob
        return self.logo_mime is not None

    @property
    def vs_prefix(self) -> int:
        """The YYNN an issued variable symbol starts with; display only."""
        return (self.vs_year % 100) * 100 + self.vs_series

    @property
    def shows_eur(self) -> bool:
        """Whether EUR is an accepted second currency alongside the local one.
        False for an EUR-priced tournament (its local figure already is the
        EUR one) — the single condition every EUR presentation, pricing, and
        matching path consults. Does not depend on eur_rate, which is a Setup
        convenience only and plays no part in whether EUR applies."""
        return self.eur_payments_enabled and self.local_currency != Currency.EUR

    owner: Mapped[Fencer | None] = relationship(foreign_keys=[owner_id])
    disciplines: Mapped[list[Discipline]] = relationship(back_populates="tournament")
    extra_items: Mapped[list[ExtraItem]] = relationship(back_populates="tournament")
    registrations: Mapped[list[Registration]] = relationship(back_populates="tournament")
    # account-based console access rows (exposed via the /team API); distinct
    # from `organizers`, the public-facing titular-organizer name+link list
    console_organizers: Mapped[list[TournamentOrganizer]] = relationship(
        back_populates="tournament"
    )


class Discipline(Base):
    """A competition category offered by one tournament.

    Identity is the slug: short, stable, organizer-visible, unique within the
    tournament. Classification is the three facets — weapon, gender,
    material — carried separately, so several disciplines MAY share a
    classification (tiers, or individual-plus-team in one weapon). No field
    here is called `code`: that name is what collapsed identity and
    classification together before this split (design discipline-identity D5).
    """

    __tablename__ = "disciplines"
    __table_args__ = (UniqueConstraint("tournament_id", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    slug: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    # classification: the five taxonomy weapons are offered as suggestions,
    # but any weapon is accepted (design discipline-identity D4); gender and
    # material stay closed sets
    weapon: Mapped[str] = mapped_column(String(30))
    gender: Mapped[str] = mapped_column(String(1))
    material: Mapped[str] = mapped_column(String(10))
    # individual or team (design team-disciplines D1); frozen once any
    # RegistrationDiscipline or Team references this row (enforced in the
    # router, not here). For a TEAM discipline, capacity counts teams and fee/
    # fee_early/fee_eur/fee_early_eur are per team, not per member (design D2)
    kind: Mapped[DisciplineKind] = mapped_column(
        str_enum(DisciplineKind), default=DisciplineKind.INDIVIDUAL
    )
    team_min: Mapped[int | None]
    team_max: Mapped[int | None]
    capacity: Mapped[int]
    # unit price; nullable so a Setup row can exist before pricing is decided
    # (setup_missing gates registration until every discipline is priced)
    fee: Mapped[int | None]
    fee_early: Mapped[int | None]
    # EUR prices, present only in local + EUR mode. Authoritative organizer
    # decisions, never derived from fee/fee_early (design Decision 1) — see
    # Tournament.eur_rate for the one place a rate is allowed to touch money.
    fee_eur: Mapped[int | None]
    fee_early_eur: Mapped[int | None]
    # optional schedule (mainly multi-day events) and ruleset reference; purely
    # informational, never touches pricing
    schedule_when: Mapped[str | None] = mapped_column(String(200))
    schedule_where: Mapped[str | None] = mapped_column(String(300))
    ruleset_name: Mapped[str | None] = mapped_column(String(100))
    ruleset_url: Mapped[str | None] = mapped_column(String(500))

    @property
    def taxonomy_code(self) -> str:
        """The join key to everything outside this discipline — HR category
        mapping, ratings snapshots (design discipline-identity D5). Never this
        discipline's identity: several disciplines MAY derive the same code."""
        return taxonomy.taxonomy_code(self.weapon, self.gender, self.material)

    tournament: Mapped[Tournament] = relationship(back_populates="disciplines")


class ExtraItem(Base):
    """An organizer-defined billable extra service ("afterparty saturday",
    "t-shirt"), freely named, categorized for discount scoping."""

    __tablename__ = "extra_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[ExtraCategory] = mapped_column(str_enum(ExtraCategory))
    price: Mapped[int]
    # EUR price, present only in local + EUR mode. Authoritative, never
    # derived from `price` (design Decision 1).
    price_eur: Mapped[int | None]
    # per-registration quantity limit; 1 renders as a checkbox
    max_qty: Mapped[int] = mapped_column(default=1)
    # optional descriptive fields shown when the item is presented
    # informationally; never affect pricing
    schedule_when: Mapped[str | None] = mapped_column(String(200))
    schedule_where: Mapped[str | None] = mapped_column(String(300))
    remark: Mapped[str | None] = mapped_column(String(500))
    # optional single option the fencer answers when selecting this item (e.g.
    # label "size"). With choices the answer must be one of them; without, it is
    # free text. No label means the item takes no option. Never affects pricing.
    option_label: Mapped[str | None] = mapped_column(String(50))
    option_choices: Mapped[list] = mapped_column(JSON, default=list)

    @property
    def takes_option(self) -> bool:
        return bool(self.option_label)

    tournament: Mapped[Tournament] = relationship(back_populates="extra_items")


class OrganizerRequest(Base):
    """A plea for the global Organizer role. At most one pending per account;
    decided pleas are kept as history, so re-pleading creates a new row."""

    __tablename__ = "organizer_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    fencer_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    message: Mapped[str | None] = mapped_column(Text)
    state: Mapped[RequestState] = mapped_column(
        str_enum(RequestState), default=RequestState.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("fencers.id"))

    fencer: Mapped[Fencer] = relationship(foreign_keys=[fencer_id])


class TournamentOrganizer(Base):
    __tablename__ = "tournament_organizers"
    __table_args__ = (UniqueConstraint("tournament_id", "fencer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    fencer_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))

    tournament: Mapped[Tournament] = relationship(back_populates="console_organizers")
    fencer: Mapped[Fencer] = relationship()


class Registration(Base):
    """One fencer's entry to one tournament; starts life as a reservation."""

    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("tournament_id", "fencer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    fencer_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    state: Mapped[RegistrationState] = mapped_column(
        str_enum(RegistrationState), default=RegistrationState.RESERVED
    )
    # unique across the whole deployment, not just this tournament (design
    # Decision 4); the backstop that turns a counter race into a retry
    # instead of two registrations sharing one VS
    vs: Mapped[int | None] = mapped_column(unique=True)
    total_amount: Mapped[int] = mapped_column(default=0)
    # the EUR total, stored at registration exactly as total_amount is, and
    # NULL for a tournament that does not price in EUR (design Decision 1) —
    # never recomputed on read, never moved by a later price or rate change
    total_eur: Mapped[int | None]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refundable: Mapped[bool | None]
    refund_state: Mapped[RefundState] = mapped_column(
        str_enum(RefundState), default=RefundState.NOT_APPLICABLE
    )
    # sum of payments credited to this registration in the tournament's local
    # currency, in cents — the one stored local-currency money figure; the
    # balance is always derived (see outstanding_cents), never stored
    amount_paid_cents: Mapped[int] = mapped_column(default=0)
    # the EUR sibling of amount_paid_cents: sum of EUR payments credited, in
    # EUR cents. The two counters are never summed — a registration is settled
    # when either currency's credit covers that currency's own total (design
    # Decision 5); see matching.match_new_transactions.
    amount_paid_eur_cents: Mapped[int] = mapped_column(default=0)

    @property
    def fully_queued(self) -> bool:
        """Whether this registration sits entirely below the line — every
        individual entry a substitute placement and every team waitlisted.
        Vacuously true on whichever axis carries nothing, so a team-only
        registration is judged on its teams alone (design team-disciplines
        task 5.2).

        Nothing is owed from the queue (design add-payment-modes D5), so this
        is what the confirmation email, the payment-instructions endpoint and
        the reminder pass all ask before offering or chasing money."""
        return all(entry.is_substitute for entry in self.entries) and all(
            team.waitlisted for team in self.teams
        )

    @property
    def outstanding_cents(self) -> int:
        return self.total_amount * 100 - self.amount_paid_cents

    @property
    def outstanding_eur_cents(self) -> int | None:
        """None when this registration has no EUR total to owe against."""
        if self.total_eur is None:
            return None
        return self.total_eur * 100 - self.amount_paid_eur_cents

    # legacy billable extras (pre-itemized tournaments) and free-text fields
    weapon_rentals: Mapped[list[str]] = mapped_column(JSON, default=list)
    afterparty: Mapped[bool] = mapped_column(default=False)
    aftersparring: Mapped[bool] = mapped_column(default=False)
    accommodation: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    tournament: Mapped[Tournament] = relationship(back_populates="registrations")
    fencer: Mapped[Fencer] = relationship(back_populates="registrations")
    entries: Mapped[list[RegistrationDiscipline]] = relationship(
        back_populates="registration"
    )
    extra_selections: Mapped[list[RegistrationExtra]] = relationship(
        back_populates="registration"
    )
    teams: Mapped[list[Team]] = relationship(back_populates="registration")


class RegistrationExtra(Base):
    """One registration's selection of one extra item, with quantity and the
    answer to the item's option when it declares one."""

    __tablename__ = "registration_extras"
    __table_args__ = (UniqueConstraint("registration_id", "extra_item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id"))
    extra_item_id: Mapped[int] = mapped_column(ForeignKey("extra_items.id"))
    qty: Mapped[int] = mapped_column(default=1)
    # answer to the item's option; null for items that declare none, and also
    # for selections stored before their item gained an option label
    option_value: Mapped[str | None] = mapped_column(String(100))

    registration: Mapped[Registration] = relationship(
        back_populates="extra_selections"
    )
    item: Mapped[ExtraItem] = relationship()


class BankTransaction(Base):
    """An ingested bank transaction. Natural identity is the bank's transaction
    id (external_id); ingestion is idempotent per tournament on that key.
    Amounts are stored in haléře (cents) — bank amounts carry decimals."""

    __tablename__ = "bank_transactions"
    __table_args__ = (UniqueConstraint("tournament_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    external_id: Mapped[str] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(10))  # "fio_api" | "csv"
    date: Mapped[date]
    amount_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3))
    vs: Mapped[int | None]
    message: Mapped[str | None] = mapped_column(Text)
    payer_name: Mapped[str | None] = mapped_column(String(200))
    payer_account: Mapped[str | None] = mapped_column(String(50))
    # additional Fio text fields that may carry a SEPA reference (design
    # harden-payment-matching Decision 4); NULL on every historical row, which
    # the VS scan treats as absent. Deliberately not payer_name/payer_account,
    # which searchable_text below excludes.
    user_identification: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    specification: Mapped[str | None] = mapped_column(Text)
    specific_symbol: Mapped[str | None] = mapped_column(String(50))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # matching outcome; None until the matcher has processed the transaction
    status: Mapped[str | None] = mapped_column(String(20))  # matched|unmatched|flagged|partial
    status_reason: Mapped[str | None] = mapped_column(String(50))
    matched_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id")
    )
    # when the matcher last considered this transaction — set on every pass
    # that examines it (new or re-evaluated flagged), so a row leaving the
    # queue between passes is explicable (design Decision 2)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tournament: Mapped[Tournament] = relationship()
    matched_registration: Mapped[Registration | None] = relationship()

    @property
    def searchable_text(self) -> str:
        """Every text-bearing field the VS scan may search, concatenated.
        Deliberately excludes payer_name and payer_account: both are
        structured identifiers (an account number is a long digit string),
        and scanning them for a bare numeric VS is a false-positive generator
        with no upside (design Decision 4)."""
        parts = [
            self.message,
            self.user_identification,
            self.comment,
            self.specification,
            self.specific_symbol,
        ]
        return " ".join(part for part in parts if part)


class PaymentEvent(Base):
    """Audit trail of payment lifecycle events (matches, mismatches, reminders,
    expiries, reinstatements, amendments). `kind` is a free string rather than
    an enum; besides the events already named above it also takes
    `reinstated_in_grace`, `reinstated_by_organizer`, `marked_for_refund`, and
    `registration_amended`."""

    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    registration_id: Mapped[int | None] = mapped_column(ForeignKey("registrations.id"))
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transactions.id"))
    kind: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Rule(Base):
    """A persisted manual operation, replayed in creation order on every rerun.

    Soft-deleted rules are excluded from replay — data-side, as if they never
    existed. Their history lives in the append-only rule journal.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    phase: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(30))
    target: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("fencers.id"))

    author: Mapped[Fencer] = relationship(foreign_keys=[created_by])


class RuleJournalEntry(Base):
    """Append-only meta-journal of rule lifecycle events. Never replayed."""

    __tablename__ = "rule_journal"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"))
    action: Mapped[str] = mapped_column(String(10))  # created | updated | deleted
    actor_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    content: Mapped[dict] = mapped_column(JSON)  # rule snapshot at event time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HRFighter(Base):
    """One fighter from the hemaratings.com index. Global per deployment;
    the whole table is replaced by a successful refresh."""

    __tablename__ = "hr_fighters"

    hr_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(200))
    name_folded: Mapped[str] = mapped_column(String(200), index=True)
    nationality: Mapped[str | None] = mapped_column(String(100))
    club: Mapped[str | None] = mapped_column(String(200))


class HRIndexRefresh(Base):
    """Log of index refresh attempts, successful and rejected — the operator's
    diagnostics when the source format drifts."""

    __tablename__ = "hr_index_refreshes"

    id: Mapped[int] = mapped_column(primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(10))  # ok | rejected | failed
    fighter_count: Mapped[int | None]
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class HRRatingSnapshot(Base):
    """A dated fetch of ratings for one tournament's fencers. Exports use the
    latest snapshot (Decision 8: dated schema, latest-only UI)."""

    __tablename__ = "hr_rating_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fencer_count: Mapped[int]

    ratings: Mapped[list[HRSnapshotRating]] = relationship(back_populates="snapshot")


class HRSnapshotRating(Base):
    __tablename__ = "hr_snapshot_ratings"
    __table_args__ = (UniqueConstraint("snapshot_id", "hr_id", "discipline_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("hr_rating_snapshots.id"))
    hr_id: Mapped[int]
    # a taxonomy code (design discipline-identity D5), not a discipline's
    # identity — one rating per fencer per classification, shared by every
    # discipline that classification is
    discipline_code: Mapped[str] = mapped_column(String(15))
    rating: Mapped[float | None]
    rank: Mapped[int | None]

    snapshot: Mapped[HRRatingSnapshot] = relationship(back_populates="ratings")


class ImportBatch(Base):
    """One uploaded registration table. The newest batch is the active source
    for imported rows; older batches remain as provenance."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    filename: Mapped[str] = mapped_column(String(300))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    row_count: Mapped[int]


class ImportedRow(Base):
    """A source row of an uploaded table, kept verbatim for provenance.

    `key` is a content fingerprint: unchanged rows keep it across re-uploads,
    so parse decisions and rules targeting "imp:<key>" survive."""

    __tablename__ = "imported_rows"
    __table_args__ = (UniqueConstraint("batch_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"))
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    row_number: Mapped[int]
    key: Mapped[str] = mapped_column(String(20))
    raw: Mapped[dict] = mapped_column(JSON)

    batch: Mapped[ImportBatch] = relationship()


class ImportDecision(Base):
    """A materialized LLM (or organizer) output: parse, match proposal, merge
    proposal, dedup classification. Reruns reuse decisions; only keys without
    one invoke the LLM (spec: decision persistence and incrementality)."""

    __tablename__ = "import_decisions"
    __table_args__ = (UniqueConstraint("tournament_id", "kind", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    kind: Mapped[str] = mapped_column(String(20))  # parse | hr_match | merge | dedup
    key: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(20), default="llm")  # llm | organizer
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RegistrationDiscipline(Base):
    """A registration's entry into one discipline; substitutes queue by registration time."""

    __tablename__ = "registration_disciplines"
    __table_args__ = (UniqueConstraint("registration_id", "discipline_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id"))
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id"))
    is_substitute: Mapped[bool] = mapped_column(default=False)

    registration: Mapped[Registration] = relationship(back_populates="entries")
    discipline: Mapped[Discipline] = relationship()


class Team(Base):
    """One team, entered into one team discipline by one fencer through that
    fencer's own registration — billed on that registration's total, owed
    against its VS, carrying no VS, expiry, or payment window of its own
    (design team-disciplines D1). A registration may carry several teams, in
    the same discipline or different ones; nothing here deduplicates by name
    (design D9)."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id"))
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id"))
    name: Mapped[str] = mapped_column(String(200))
    waitlisted: Mapped[bool] = mapped_column(default=False)
    # set once a composition reminder has been sent, so a later tick does not
    # resend it (design D7); unrelated to registration.reminded_at
    composition_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    registration: Mapped[Registration] = relationship(back_populates="teams")
    discipline: Mapped[Discipline] = relationship()
    members: Mapped[list[TeamMember]] = relationship(
        back_populates="team", order_by="TeamMember.ordinal", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    """A named roster entry — never a `Fencer`: `Fencer.email` is unique and
    non-nullable, and most roster members neither have nor will ever have a
    Squire account (design team-disciplines D4). `hr_id` null is the expected
    case for an HR-unknown member, not a degraded one; no uniqueness
    constraint, since identity is local to this roster (two rosters naming the
    same person produce two independent rows)."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    name: Mapped[str] = mapped_column(String(200))
    hr_id: Mapped[int | None] = mapped_column(index=True)
    club: Mapped[str | None] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(100))

    team: Mapped[Team] = relationship(back_populates="members")
