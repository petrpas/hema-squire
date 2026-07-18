"""Core multi-tenant data model.

Money amounts are whole CZK stored as integers. Fencer accounts are global;
everything else is tournament-scoped.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UnpaidListTreatment(enum.StrEnum):
    HIDDEN = "hidden"
    GREYED = "greyed"


class RegistrationState(enum.StrEnum):
    RESERVED = "reserved"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RefundState(enum.StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    REFUNDED = "refunded"


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
    hr_id: Mapped[int | None] = mapped_column(unique=True)
    nationality: Mapped[str | None] = mapped_column(String(100))
    club: Mapped[str | None] = mapped_column(String(200))
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

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    date: Mapped[date]
    language: Mapped[str] = mapped_column(String(10), default="cs")

    # payment and reservation parameters
    reservation_validity_days: Mapped[int] = mapped_column(default=10)
    reminder_day: Mapped[int] = mapped_column(default=5)
    amount_tolerance_percent: Mapped[int] = mapped_column(default=5)
    refundable_until: Mapped[date | None]
    bank_account: Mapped[str | None] = mapped_column(String(50))
    unpaid_list_treatment: Mapped[UnpaidListTreatment] = mapped_column(
        str_enum(UnpaidListTreatment), default=UnpaidListTreatment.GREYED
    )

    fio_token: Mapped[str | None] = mapped_column(String(200))

    # billable extras; early-bird prices apply within the optional window
    early_bird_until: Mapped[date | None]
    weapon_rental_fee: Mapped[int] = mapped_column(default=0)
    weapon_rental_fee_early: Mapped[int | None]
    afterparty_fee: Mapped[int] = mapped_column(default=0)
    afterparty_fee_early: Mapped[int | None]

    disciplines: Mapped[list[Discipline]] = relationship(back_populates="tournament")
    registrations: Mapped[list[Registration]] = relationship(back_populates="tournament")
    organizers: Mapped[list[TournamentOrganizer]] = relationship(back_populates="tournament")


class Discipline(Base):
    """A competition category offered by one tournament.

    Codes come from the HEMA taxonomy (weapon LS/SA/RA/RD/SB x gender x material).
    """

    __tablename__ = "disciplines"
    __table_args__ = (UniqueConstraint("tournament_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int]
    fee: Mapped[int]
    fee_early: Mapped[int | None]

    tournament: Mapped[Tournament] = relationship(back_populates="disciplines")


class TournamentOrganizer(Base):
    __tablename__ = "tournament_organizers"
    __table_args__ = (UniqueConstraint("tournament_id", "fencer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    fencer_id: Mapped[int] = mapped_column(ForeignKey("fencers.id"))

    tournament: Mapped[Tournament] = relationship(back_populates="organizers")
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
    vs: Mapped[int | None] = mapped_column(unique=True)
    total_amount: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refundable: Mapped[bool | None]
    refund_state: Mapped[RefundState] = mapped_column(
        str_enum(RefundState), default=RefundState.NOT_APPLICABLE
    )

    # billable extras and free-text fields
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
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # matching outcome; None until the matcher has processed the transaction
    status: Mapped[str | None] = mapped_column(String(20))  # matched|unmatched|flagged
    status_reason: Mapped[str | None] = mapped_column(String(50))
    matched_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id")
    )

    tournament: Mapped[Tournament] = relationship()
    matched_registration: Mapped[Registration | None] = relationship()


class PaymentEvent(Base):
    """Audit trail of payment lifecycle events (matches, mismatches, reminders,
    expiries)."""

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
