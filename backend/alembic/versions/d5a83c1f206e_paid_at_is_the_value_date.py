"""paid_at carries the day the money arrived, not the day it was imported

Revision ID: d5a83c1f206e
Revises: c4f2a91b7e30
Create Date: 2026-09-06 00:00:00.000000

Every settled registration in the database was dated by the clock at the moment
matching ran, which for an imported statement is the day somebody pressed
import. The day the money actually arrived was already stored beside it, on the
transaction.

This rewrites what can be rewritten: for each paid registration with at least
one bank transaction matched to it, the start of `MAX(bank_transactions.date)`
in the tournament's own zone. The latest rather than the earliest, because a
registration settled by two statements was covered when the second arrived; at
migration time the whole history is visible, which is exactly what the live
path lacks (design paid-at-is-value-date D3, D6).

Rows with no matched transaction keep the value they have. Two kinds are
concerned and both are deliberate:

  * a registration settled by hand records no payment, has no statement day
    behind it, and correctly carries the moment of the mark;
  * a registration settled by a payment the organizer recorded could in
    principle take its `received_on`, but a registration may hold both a
    transaction and a recorded payment, and deciding which wins is a rule no
    reader has asked for. Those rows keep a value wrong by a day or two rather
    than gaining one wrong by a rule; the recorded payment states its own
    `received_on` where the organizer reads it.

There is no downgrade. The overwritten instants are not recoverable from
`registrations`, but they are recoverable in substance from
`payment_events.created_at`, which timestamps the `payment_matched` event for
every row this touches — so the downgrade says so rather than pretending to
restore them.
"""
import datetime
import zoneinfo
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5a83c1f206e'
down_revision: str | Sequence[str] | None = 'c4f2a91b7e30'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TIMEZONE = "Europe/Prague"


def _zone(name: str | None) -> zoneinfo.ZoneInfo:
    """The same fallback `app.setup` makes: a zone identifier the database no
    longer knows costs an hour, not a row."""
    try:
        return zoneinfo.ZoneInfo(name or DEFAULT_TIMEZONE)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)


def _as_date(value) -> datetime.date | None:
    """`MAX()` over a Date column comes back as a date on some drivers and as
    an ISO string on SQLite."""
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value)[:10])


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT r.id AS registration_id,
                   t.timezone AS timezone,
                   MAX(b.date) AS value_date
            FROM registrations r
            JOIN tournaments t ON t.id = r.tournament_id
            JOIN bank_transactions b ON b.matched_registration_id = r.id
            WHERE r.paid_at IS NOT NULL
            GROUP BY r.id, t.timezone
            """
        )
    ).mappings().all()

    for row in rows:
        value_date = _as_date(row["value_date"])
        if value_date is None:
            continue
        paid_at = datetime.datetime.combine(
            value_date, datetime.time(0, 0), tzinfo=_zone(row["timezone"])
        ).astimezone(datetime.UTC)
        connection.execute(
            sa.text("UPDATE registrations SET paid_at = :paid_at WHERE id = :id"),
            {"paid_at": paid_at, "id": row["registration_id"]},
        )


def downgrade() -> None:
    """Deliberately empty. See the module docstring: the instants this replaced
    live on in `payment_events.created_at`, and a downgrade claiming to restore
    them from `registrations` would be inventing them."""
