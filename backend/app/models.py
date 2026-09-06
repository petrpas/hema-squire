"""Core multi-tenant data model.

Money amounts are whole units of the tournament's local currency, stored as
integers. A tournament that also accepts EUR stores a second, independent
whole-unit EUR figure alongside each local one — never derived from it.
Fencer accounts are global; everything else is tournament-scoped.
"""

import enum
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import constraints, taxonomy
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
    CANCELLED = "cancelled"


class UnpaidListTreatment(enum.StrEnum):
    HIDDEN = "hidden"
    GREYED = "greyed"


class RegistrationsKeptBy(enum.StrEnum):
    """Who keeps a tournament's list of entrants.

    `SQUIRE` is the product as it has always worked: fencers register in the
    application and Squire manages what follows — the window, the clocks, the
    mail, the queue. `ORGANIZER` says the list is maintained somewhere else and
    reaches Squire by import, so Squire cleans, matches, prices and exports it
    and runs nothing against it.

    **This is the tournament's mode, and the only thing so called.** It
    qualifies because it is stored, has two values and changes what the system
    does. The `feature_*` flags are not a mode: three of them govern which
    controls Setup offers and change nothing a fencer experiences, and the
    fourth is the payments setting, which stands beside this one (spec
    tournament-mode, tournament-features).

    Never derived from what the tournament holds. A tournament that has been
    imported into is not organizer-kept on that evidence, and one that has been
    registered for is not Squire-kept on that evidence; the guarantee has to
    hold from the moment the tournament exists, before either has happened."""

    SQUIRE = "squire"
    ORGANIZER = "organizer"


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


class OperationKind(enum.StrEnum):
    """The kinds of console work that run as a recorded operation. Each is a
    run of one LLM-backed step of the ETL console; the HR index refresh is not
    among them, being a property of the deployment rather than of a
    tournament."""

    PARSE = "parse"
    MATCH = "match"
    DEDUP = "dedup"
    # interpreting a bank statement no exact reader recognises
    # (design add-payments-intake D3)
    STATEMENT = "statement"


class OperationStatus(enum.StrEnum):
    """DONE and FAILED are how work ends of its own accord. INTERRUPTED is how
    it ends when the process running it did not survive: the startup sweep
    writes it, and it is not an error — the work stopped partway and running it
    again finishes it (design D5)."""

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


def str_enum(enum_cls: type[enum.StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
        length=30,
    )


class Fencer(Base):
    """Global, portable fencer account, ideally bound to a HEMA Ratings profile.

    Two records wearing one name. For a fencer who signs up it is a login — an
    address and a password hash, portable between tournaments. For a fencer the
    organizer enrols on the tournament's behalf it is only a person on a roster:
    no credentials, never written to, not something anyone can log into (spec
    `fencer-accounts`, "A fencer record may exist without an account").
    """

    __tablename__ = "fencers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable, because an address identifies an *account* and a record that
    # cannot be logged into needs none. Requiring one made the organizer write
    # an address that was not the fencer's — a parent's, a club
    # representative's, entered once for several people — and refused to enrol
    # the second and third of them at all.
    #
    # Still unique where present: an address that exists is still a login, and
    # NULL is not equal to NULL in either SQLite or Postgres, so the index
    # admits any number of them.
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
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
    # where this tournament's registration is held when Squire does not hold it
    # (spec external-registration). Mandatory to publish a tournament the
    # organizer keeps, optional otherwise. Squire never fetches it, never checks
    # that it resolves and never reports it as dead: what it points at is not
    # Squire's to know, and a check made at save time proves nothing about the
    # moment a fencer follows it (design add-external-registration D1)
    external_registration_url: Mapped[str | None] = mapped_column(
        String(constraints.EXTERNAL_REGISTRATION_URL_MAX_LENGTH)
    )
    # public-facing titular organizers (clubs/entities), each {"name", "link"};
    # independent of the account-based console access in TournamentOrganizer.
    # Entries may still be bare strings from a partially-migrated or
    # restored-from-old-export deployment; read via organizers_list().
    organizers: Mapped[list] = mapped_column(JSON, default=list)
    registration_opens: Mapped[date | None]
    # the wall-clock time registration opens on `registration_opens`, read in
    # this tournament's `timezone`. Unset means the start of that local day,
    # which is what a tournament carrying only the date has always meant. It is
    # a child of the date, never a value of its own: clearing the date clears
    # it (design add-registration-open-time D9)
    registration_opens_time: Mapped[time | None]
    registration_closes: Mapped[date | None]
    # freezes the roster for amendments independently of registration close;
    # unset means "same window as registration" (setup.amendment_availability)
    amendments_close: Mapped[date | None]
    # the date by which team rosters are expected to reach their disciplines'
    # minimum size; meaningful only when a team discipline exists. Checks, it
    # never enforces — no roster is locked, no team is cancelled or waitlisted,
    # and no capacity is freed on account of it (design team-disciplines D7)
    team_composition_deadline: Mapped[date | None]

    # this tournament's own local zone, as an IANA identifier. Every date on
    # the timeline is read as a day in it and the opening time as a wall clock
    # in it — not just the opening, or a tournament would open at 18:00 local
    # and close at 01:59 local (design add-registration-open-time D2). Non-null
    # with a default: a nullable zone would leave every read site to decide
    # what NULL means, and they would drift
    timezone: Mapped[str] = mapped_column(String(64), default=constraints.DEFAULT_TIMEZONE)

    # Four stored flags, of two kinds — and the difference is the point.
    #
    # `feature_schedule`, `feature_teams` and `feature_extras` are features in
    # the sense `tournament-features` fixes: each governs which controls Setup
    # offers and changes nothing a fencer experiences. A hidden extra item is
    # still sold, a hidden team discipline still takes teams.
    #
    # `feature_payments` is not one of those. It suspends the payment
    # machinery — no window, no mail, no reconciliation (spec payments) — and
    # so stands beside the tournament's mode, `registrations_kept_by` below,
    # as the second setting that changes what Squire does rather than what it
    # shows. It is stored here because it always has been, not because it is
    # the same kind of thing.
    #
    # No name is derived from how many are enabled. There is no easy or
    # advanced mode: that named a state nothing stored, and every surface had
    # to compute it (spec tournament-features). And none is re-derived from
    # the tournament's contents — adding a team discipline does not turn
    # feature_teams on. They record what the organizer asked to see.
    feature_schedule: Mapped[bool] = mapped_column(default=False)
    feature_payments: Mapped[bool] = mapped_column(default=False)
    feature_teams: Mapped[bool] = mapped_column(default=False)
    feature_extras: Mapped[bool] = mapped_column(default=False)

    # The tournament's **mode**, and the only thing in the product so called
    # (spec tournament-mode): `SQUIRE` is automatic mode, `ORGANIZER` manual.
    # Stored under this name rather than as `mode` because a column reading
    # `manual` would not say manual what; every surface an organizer reads
    # calls it the mode.
    #
    # Manual mode closes in-app registration and takes the tournament out of
    # the scheduler's pass entirely — a structural exclusion rather than a
    # per-registration check, so a registration created by any path is safe by
    # construction. Every tournament predating this is `SQUIRE`, which is what
    # all of them were
    registrations_kept_by: Mapped[RegistrationsKeptBy] = mapped_column(
        str_enum(RegistrationsKeptBy), default=RegistrationsKeptBy.SQUIRE
    )

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
    # the shipped default was 10, before the 2-7 range existed; live
    # tournaments that predate it still carry 10 (design add-payment-modes
    # Decision 9, enforced on write only). A tournament created since then
    # gets the range's max instead, so the field it lands on already matches
    # the hint text a new organizer reads next to it.
    reservation_validity_days: Mapped[int] = mapped_column(
        default=constraints.RESERVATION_VALIDITY_DAYS_MAX
    )
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

    @property
    def fio_token_configured(self) -> bool:
        """Whether the bank API can be polled at all. The token itself never
        leaves the server; the console needs only this."""
        return bool(self.fio_token)

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
    disciplines: Mapped[list[Discipline]] = relationship(
        back_populates="tournament", order_by=lambda: [Discipline.ordinal, Discipline.id]
    )
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
    # display order among the tournament's disciplines, organizer-set via the
    # Setup table's up arrow; ties (e.g. a row created without one) fall back
    # to `id`, which is what an unordered tournament already sorted by
    ordinal: Mapped[int] = mapped_column(default=0)
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
    # informational, never touches pricing. The ruleset is inline markdown
    # (`organizer-prose`), so one field carries the name and any links to the
    # rules — several, when they are published in several languages.
    schedule_when: Mapped[str | None] = mapped_column(String(200))
    schedule_where: Mapped[str | None] = mapped_column(String(300))
    ruleset: Mapped[str | None] = mapped_column(String(500))

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
    # Both lifecycle clocks are dormant for this registration, by virtue of its
    # origin: it was issued for a row that states who is competing rather than
    # taken from someone registering now (spec imported-registrations, "An
    # issued registration's clocks never start"). It carries no due date, opens
    # no payment window, never expires for non-payment, is never reminded, and
    # is never demoted when seating settles — permanently, whatever the
    # tournament's payments feature, payment mode or seating deadline later
    # says.
    #
    # `registration` already knows this idea: both clocks are dormant while the
    # payments feature is off. This is the same dormancy reached by a second
    # cause, so it is a property of the registration rather than a test the
    # scheduler makes — a stored fact is one thing to get right in one place,
    # and forgetting an origin test in one of four passes mails people who
    # registered a season ago (design Decision 3).
    #
    # What is dormant is the passage of time, not the money: an issued
    # registration is matched, linked and credited like any other.
    clocks_dormant: Mapped[bool] = mapped_column(default=False)
    # The fencer-list row this registration was issued for — `imp:<key>` or
    # `man:<id>` — where it was issued rather than made by someone registering.
    #
    # It is the row's identity, not a back-reference: the registration takes the
    # row's place in the fencer list under this id, so the fencer keeps the
    # fixed number they were given when the row was born (spec etl-console,
    # Fixed fencer number) and the list does not show them twice, once as a row
    # and once as a registration.
    source_row_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refundable: Mapped[bool | None]
    refund_state: Mapped[RefundState] = mapped_column(
        str_enum(RefundState), default=RefundState.NOT_APPLICABLE
    )
    # Sum of payments credited to this registration in the tournament's local
    # currency, in cents — the one stored local-currency money figure; the
    # balance is always derived (see outstanding_cents), never stored.
    #
    # This counter used to mean *money Squire saw in a statement*. It now means
    # **money credited, by a statement or by a person who said so**: an
    # organizer may record a payment that arrived outside the bank feed, and it
    # is credited here exactly as an ingested transaction's amount is (spec
    # payments, "An organizer may record a payment Squire never saw"). Where
    # the money came from is a property of the payment, not of this figure —
    # ask `ManualPayment` and `BankTransaction`, which is how the two are told
    # apart after the fact.
    #
    # A second counter was rejected deliberately: five readers would each have
    # to remember to sum two fields, and the one that forgot would be a
    # reservation expiring on money the organizer was told had arrived (design
    # add-manual-payment-entry D1).
    #
    # A registration settled by hand credits **nothing** here. That mark is a
    # waiver, not a payment; see `settled_by_hand_at`.
    amount_paid_cents: Mapped[int] = mapped_column(default=0)
    # the EUR sibling of amount_paid_cents: sum of EUR payments credited, in
    # EUR cents. The two counters are never summed — a registration is settled
    # when either currency's credit covers that currency's own total (design
    # Decision 5); see matching.match_new_transactions.
    amount_paid_eur_cents: Mapped[int] = mapped_column(default=0)
    # When an organizer said this registration is settled with nothing passing
    # through Squire, and why. One mark meaning one thing on every kind of
    # tournament: where Squire collects nothing it is the organizer's word that
    # they took the money themselves, and where Squire collects it is a waiver
    # — a free place, a comped entrant (spec payments, "An organizer may mark a
    # registration settled by hand").
    #
    # Stored rather than deduced from a paid state with empty counters. That
    # deduction was sound only while such a registration could have no other
    # cause; it now can, since a waived registration may also hold a payment
    # recorded by hand (design add-manual-payment-entry D4).
    #
    # The reason is required where the tournament's payments are Squire's and
    # optional where they are not — enforced at the endpoint, since it is a
    # fact about the tournament rather than about this row.
    settled_by_hand_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_by_hand_reason: Mapped[str | None] = mapped_column(String(200))

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
    def holds_queued_placement(self) -> bool:
        """Whether any part of this registration sits below the line — one
        substitute entry or one waitlisted team is enough.

        Distinct from `fully_queued`, which asks whether *everything* is below
        it. This is the question a lapsing payment window asks: a registration
        with anything in the queue is demoted rather than expired, so that
        money owed for a seat never costs a queue place that owed nothing
        (spec: registration, "Reservation lifecycle")."""
        return any(entry.is_substitute for entry in self.entries) or any(
            team.waitlisted for team in self.teams
        )

    @property
    def audit_label(self) -> str:
        """How this registration names itself in an audit line or an event.

        Its variable symbol where it has one, because that is what an organizer
        reading a bank statement sees. Where it has none — a registration on a
        tournament whose organizer keeps the roster, which Squire never gave a
        symbol to quote — the fencer, which is what identifies it there. Never
        "VS None", which is a line that says the symbol is missing rather than
        that there was never one to miss."""
        if self.vs is not None:
            return f"VS {self.vs}"
        return f"registrace {self.id} ({self.fencer.display_name})"

    @property
    def outstanding_cents(self) -> int:
        # Correct under the widened counter without change: what is owed is the
        # total less what has been credited, whether a statement or a person
        # put the credit there. A registration settled by hand is the one case
        # this figure does not answer on its own — nothing was credited and
        # nothing is due — and the surfaces read `settled_by_hand_at` beside it
        # and say *waived* (design add-manual-payment-entry D5).
        return self.total_amount * 100 - self.amount_paid_cents

    @property
    def outstanding_eur_cents(self) -> int | None:
        """None when this registration has no EUR total to owe against."""
        if self.total_eur is None:
            return None
        return self.total_eur * 100 - self.amount_paid_eur_cents

    def tolerance_cents(self, tournament: "Tournament", which: str) -> float:
        """Tolerance as a percentage of the registration's stable total in this
        currency lane — not of a shrinking remainder, which would tighten with
        every partial payment already credited."""
        total = self.total_amount if which == "local" else (self.total_eur or 0)
        return total * 100 * tournament.amount_tolerance_percent / 100

    def balance_cents(self, tournament: "Tournament") -> tuple[int, Currency]:
        """What is still owed — or, negative, what is over — and the currency
        that figure is stated in. One number, never two.

        The local and EUR totals are two prices for one place, not two halves
        of a debt: whichever lane the money arrives in settles the
        registration, and the other lane's untouched total is then not a
        balance at all. Printed side by side they read as a conversion, and a
        fencer who had paid 1 100 Kč in full was shown "0 Kč (45 €)" — a
        demand aimed at someone who owed nothing. So the lane the money
        actually came in decides, and where none has come the local one does,
        that being the price the tournament quotes first.

        **The tolerance decides the state, not this figure.** A settled
        registration short of its total still says how short: a euro transfer
        the payer's bank converted lands twenty or forty crowns under the local
        price, the tolerance accepts it as payment and the registration becomes
        paid — and the organizer is still owed the truth about what reached the
        account. Zeroing it here left nine such rows on one tournament reading
        "0 Kč" with money missing behind every one of them, and nothing
        anywhere that could add it up (owner decision, 2026-09-06).

        So what is quoted is what is quoted, and whether to chase it is the
        organizer's to decide rather than this method's to pre-empt. A trivial
        overpayment reads as the negative figure it is, for the same reason.

        A waiver is the one exception and owes nothing at all, whatever its
        counters hold, because no money was ever supposed to pass.
        """
        remaining, currency = self.remaining_cents(tournament)
        if self.settled_by_hand_at is not None:
            return 0, currency
        return remaining, currency

    def remaining_cents(self, tournament: Tournament) -> tuple[int, Currency]:
        """The same figure `balance_cents` states, before the waiver is applied
        to it: what the counters leave uncovered, in the lane the money came
        in.

        A waiver forgives whatever stood at the moment it was given, and that
        is not always the whole price — a fencer who paid part and had the rest
        written off is owed a console cell saying which part (owner decision,
        2026-09-06). `balance_cents` cannot say it, because a waiver owes
        nothing and its figure is therefore zero; this is where the amount the
        waiver forgave is still readable.
        """
        if self.amount_paid_eur_cents and not self.amount_paid_cents and self.total_eur is not None:
            return self.outstanding_eur_cents or 0, Currency.EUR
        return self.outstanding_cents, tournament.local_currency

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
    # Who this payment is *for*, as the row's own text named them — read out of
    # the statement at parse time and never the payer (spec
    # name-assisted-matching). One person routinely pays for another: the payer
    # names who paid, this names who it is for, and conflating them credits the
    # wrong fencer precisely when the payer is competing too. Null where the
    # text named nobody, which is an honest answer the resolver weighs.
    named_person: Mapped[str | None] = mapped_column(Text)
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

    # matching outcome; None until the matcher has processed the transaction.
    # `likely` is a *proposal* and not an outcome: the resolver read a fencer's
    # name in the payer's own words and is asking a person. No money moves, no
    # balance changes and no mail is sent while a transaction sits in it —
    # crediting is by variable symbol alone, whether the payer quoted one or the
    # organizer supplied it by confirming (spec name-assisted-matching).
    status: Mapped[str | None] = mapped_column(
        String(20)
    )  # matched|unmatched|flagged|partial|likely
    status_reason: Mapped[str | None] = mapped_column(String(50))
    matched_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id")
    )
    # the fencer a `likely` proposal names. Points at the person, not their
    # registration: what the resolver read was a name, and the registration is
    # looked up when the organizer confirms
    proposed_fencer_id: Mapped[int | None] = mapped_column(ForeignKey("fencers.id"))
    # fencers the organizer has refused for *this* payment, so the resolver does
    # not offer the same wrong answer twice. Per payment rather than per fencer:
    # a name that mis-attracts one payment has not thereby stopped being
    # somebody's name (design, Open Questions)
    rejected_fencer_ids: Mapped[list] = mapped_column(JSON, default=list)
    # when the matcher last considered this transaction — set on every pass
    # that examines it (new or re-evaluated flagged), so a row leaving the
    # queue between passes is explicable (design Decision 2)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tournament: Mapped[Tournament] = relationship()
    matched_registration: Mapped[Registration | None] = relationship()
    proposed_fencer: Mapped[Fencer | None] = relationship()

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


class PaymentMethod(enum.StrEnum):
    """How money an organizer recorded by hand arrived. A short closed set with
    an `OTHER` beside a free note, because "how did it arrive" is the first
    question asked of a payment nobody can look up in a statement."""

    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    OTHER = "other"


class ManualPayment(Base):
    """A payment the organizer says arrived, which Squire never saw: cash at
    the desk, a transfer to another account, a card terminal.

    **A sibling of `BankTransaction`, deliberately not a row inside it.** The
    transaction list is the statement ledger — what an organizer reads against
    their bank account and what intake deduplicates against — and a row no bank
    sent would falsify it for every reader of that table, for the convenience
    of this one writer. The provenance question is answered by asking a
    different table, not by filtering that one (design
    add-manual-payment-entry D2).

    Always against a registration: there is no unmatched queue for money a
    person entered, because they entered it against somebody.

    Removal is a soft delete, so a wrong entry and its reversal both survive.
    The amount reversed is this row's own `amount_cents` — never a figure
    derived from today's balance, which is the mistake the payment-link rules
    were built to avoid (`matching.py:751`). A correction is a removal and a
    new record; there is no edit."""

    __tablename__ = "manual_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id"))
    amount_cents: Mapped[int]
    # one of the tournament's currencies; credited to that currency's lane and
    # never converted, since the two lanes are never summed (see
    # Registration.amount_paid_cents)
    currency: Mapped[Currency] = mapped_column(str_enum(Currency))
    # the date the organizer says the money arrived, which is not the date they
    # typed it in. Provenance rather than a clock: reminders and expiry read
    # `expires_at` and never this
    received_on: Mapped[date]
    method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod))
    note: Mapped[str | None] = mapped_column(Text)
    # who said so, kept as the label the audit trail uses rather than a
    # foreign key: the record must still read correctly when the account that
    # made it is gone
    recorded_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tournament: Mapped[Tournament] = relationship()
    registration: Mapped[Registration] = relationship()


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
    so parse decisions and rules targeting "imp:<key>" survive.

    Unique per tournament, not per batch: a row belongs to the tournament, and
    an upload carrying content already imported is recognised at intake and
    takes in nothing (spec table-import, Intake takes in only rows new to the
    tournament). `batch_id` records which upload first brought it."""

    __tablename__ = "imported_rows"
    __table_args__ = (UniqueConstraint("tournament_id", "key"),)

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


class ManualRow(Base):
    """A fencer the organizer entered by hand, from the console.

    The third source population beside in-app registrations and imported rows
    (spec etl-console, Manual entry of a fencer): an organizer-authored source
    record, not a registration. It states who is competing; it enrols nobody,
    so there is no account, no VS and no payment instruction behind it.

    Disciplines are held as slugs and rentals as item names, the shape the
    imported population already stores its selections in, so `sheet.py` resolves
    both the same way. Its sheet row id is "man:<id>".
    """

    __tablename__ = "manual_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    name: Mapped[str] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(100))
    club: Mapped[str | None] = mapped_column(String(200))
    hr_id: Mapped[int | None]
    email: Mapped[str | None] = mapped_column(String(320))
    # the moment the organizer states the fencer registered, which is what the
    # fencer list sorts on — not the moment the row was typed
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    disciplines: Mapped[list] = mapped_column(JSON, default=list)
    weapon_rentals: Mapped[list] = mapped_column(JSON, default=list)
    afterparty: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SheetRowNumber(Base):
    """The fixed number a row carries in one tournament's fencer table.

    Keyed by the sheet row id ("reg:<id>" or "imp:<fingerprint>"), which is
    stable across reruns and re-uploads, so an unchanged imported row keeps its
    number with no special case. Allocated once, when the row enters the
    tournament, and never reissued: the number of a row deleted or merged away
    stays retired (spec etl-console, Fixed fencer number).
    """

    __tablename__ = "sheet_row_numbers"
    __table_args__ = (
        UniqueConstraint("tournament_id", "row_id"),
        UniqueConstraint("tournament_id", "number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    row_id: Mapped[str] = mapped_column(String(50))
    number: Mapped[int]


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
    """A named roster entry — never a `Fencer`: identity here is local to this
    roster, and two rosters naming the same person produce two independent rows
    (design team-disciplines D4). Most roster members neither have nor will ever
    have a Squire account.

    The original reason also cited `Fencer.email` being non-nullable, which it
    no longer is; the locality of the identity is what was doing the work and is
    what remains. `hr_id` null is the expected case for an HR-unknown member,
    not a degraded one, and carries no uniqueness constraint."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    name: Mapped[str] = mapped_column(String(200))
    hr_id: Mapped[int | None] = mapped_column(index=True)
    club: Mapped[str | None] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(100))

    team: Mapped[Team] = relationship(back_populates="members")


class Operation(Base):
    """One run of a long console operation, recorded so that it can be watched.

    The console's report on running work comes from this row and from nothing
    else — not from the response of the request that started it, which returns
    long before the work does (spec console-operations, An operation is a
    record, not a request). That is what lets a reload, a second tab, and a
    second organizer all see the same thing.

    `done` is a count of finished units, never a position in a sequence, so it
    stays correct however units are ordered (design D6). `total` counts the work
    the run will actually do: rows whose decision is already stored are reused,
    not worked on, and are not counted.

    `outcome` holds what the endpoint used to return synchronously, so the
    panels render the same shape they always did.
    """

    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    kind: Mapped[OperationKind] = mapped_column(str_enum(OperationKind))
    status: Mapped[OperationStatus] = mapped_column(
        str_enum(OperationStatus), default=OperationStatus.RUNNING
    )
    total: Mapped[int] = mapped_column(default=0)
    done: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # NULL is the running predicate, indexed with the tournament: every poll
    # asks "what is unconcluded here", and the startup sweep asks it globally
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_by: Mapped[int] = mapped_column(ForeignKey("fencers.id"))
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_operations_tournament_finished", "tournament_id", "finished_at"),)
