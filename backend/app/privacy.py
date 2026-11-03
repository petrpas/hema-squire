"""What the account holder is told and can take away (spec `privacy`): the
organizer data terms version an owner accepts, and the account's own data as
a download.

The export is the account's own view, not the tournament export (design
privacy-baseline D5): its profile and audit trail, and its registrations with
what they hold and what was credited to them. It leaves out what is another
person's — a payer's name and account, the members of a team — and what is the
organizer's — corrections, rules, notes about the row."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Fencer,
    FencerProfileAudit,
    Registration,
    RegistrationExtra,
    Team,
    Tournament,
)
from app.schemas import (
    AccountExportOut,
    ExportAuditOut,
    ExportCreditOut,
    ExportEntryOut,
    ExportExtraOut,
    ExportProfileOut,
    ExportRegistrationOut,
    ExportTeamOut,
)

# The organizer data terms in force. Changing the text in a way an owner must
# agree to again means changing this; the locale files carry the same string
# as the terms' effective date.
ORGANIZER_TERMS_VERSION = "2026-11-03"


def owns_a_tournament(session: Session, fencer: Fencer) -> bool:
    """Whether the account owns any tournament not cancelled — the one bond the
    organizer data terms bind."""
    return (
        session.scalar(
            select(Tournament.id)
            .where(Tournament.owner_id == fencer.id, Tournament.cancelled_at.is_(None))
            .limit(1)
        )
        is not None
    )


def organizer_terms_due(session: Session, fencer: Fencer) -> bool:
    return fencer.organizer_terms_version != ORGANIZER_TERMS_VERSION and owns_a_tournament(
        session, fencer
    )


def accept_organizer_terms(fencer: Fencer) -> None:
    fencer.organizer_terms_version = ORGANIZER_TERMS_VERSION
    fencer.organizer_terms_accepted_at = datetime.now(UTC)


def account_export(session: Session, fencer: Fencer) -> AccountExportOut:
    audit = session.scalars(
        select(FencerProfileAudit)
        .where(FencerProfileAudit.fencer_id == fencer.id)
        .order_by(FencerProfileAudit.changed_at, FencerProfileAudit.id)
    ).all()
    registrations = session.scalars(
        select(Registration)
        .where(Registration.fencer_id == fencer.id)
        .options(
            selectinload(Registration.tournament),
            selectinload(Registration.entries),
            selectinload(Registration.extra_selections).selectinload(RegistrationExtra.item),
            selectinload(Registration.teams).selectinload(Team.discipline),
            selectinload(Registration.credits),
        )
        .order_by(Registration.registered_at, Registration.id)
    ).all()
    return AccountExportOut(
        exported_at=datetime.now(UTC),
        profile=ExportProfileOut(
            display_name=fencer.display_name,
            email=fencer.email,
            hr_id=fencer.hr_id,
            nationality=fencer.nationality,
            club=fencer.club,
            language=fencer.language,
            role=fencer.role.value,
            created_at=fencer.created_at,
            organizer_terms_version=fencer.organizer_terms_version,
            organizer_terms_accepted_at=fencer.organizer_terms_accepted_at,
            audit=[
                ExportAuditOut(
                    field=entry.field,
                    old_value=entry.old_value,
                    new_value=entry.new_value,
                    changed_at=entry.changed_at,
                )
                for entry in audit
            ],
        ),
        registrations=[_registration(registration) for registration in registrations],
    )


def _registration(registration: Registration) -> ExportRegistrationOut:
    return ExportRegistrationOut(
        tournament=registration.tournament.display_name,
        tournament_date=registration.tournament.date,
        registered_at=registration.registered_at,
        state=registration.state.value,
        variable_symbol=registration.vs,
        total_amount=registration.total_amount,
        total_eur=registration.total_eur,
        contact_email=registration.contact_email,
        accommodation=registration.accommodation,
        notes=registration.notes,
        cancelled_at=registration.cancelled_at,
        disciplines=[
            ExportEntryOut(
                discipline=entry.discipline.name,
                is_substitute=entry.is_substitute,
                conditional=entry.conditional,
            )
            for entry in registration.entries
        ],
        extras=[
            ExportExtraOut(
                item=selection.item.name,
                category=selection.item.category.value,
                qty=selection.qty,
                option_value=selection.option_value,
            )
            for selection in registration.extra_selections
        ],
        teams=[
            ExportTeamOut(name=team.name, discipline=team.discipline.name)
            for team in registration.teams
        ],
        credits=[
            ExportCreditOut(
                amount_cents=credit.amount_cents,
                currency=credit.currency.value,
                value_date=credit.value_date,
                kind=credit.source_kind.value,
                reversed_at=credit.reversed_at,
            )
            for credit in sorted(registration.credits, key=lambda credit: credit.id)
        ],
    )
