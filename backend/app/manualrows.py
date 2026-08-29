"""Fencers the organizer entered by hand.

A manual row is a source record, not a registration (design D1): creating one
writes a `ManualRow` and allocates the fixed number it will carry for good,
exactly as an import allocates numbers at intake. Allocation happens here, where
the row is born, so `GET /sheet` stays a read.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rownumbers
from app.models import ManualRow, Tournament


def row_id(row: ManualRow) -> str:
    return f"man:{row.id}"


def rows_for(session: Session, tournament: Tournament) -> list[ManualRow]:
    """Every manual row of the tournament, in the order they were entered —
    which is the order they were numbered in."""
    return list(
        session.scalars(
            select(ManualRow)
            .where(ManualRow.tournament_id == tournament.id)
            .order_by(ManualRow.id)
        )
    )


def create(session: Session, tournament: Tournament, author_id: int, **fields) -> ManualRow:
    """Add one hand-entered fencer and give it its number, in one transaction.
    `fields` are the validated values of `ManualEntryIn`."""
    row = ManualRow(tournament_id=tournament.id, created_by=author_id, **fields)
    session.add(row)
    session.flush()
    rownumbers.allocate(session, tournament, [row_id(row)])
    session.commit()
    return row
