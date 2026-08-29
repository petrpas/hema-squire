"""Allocation of the fixed number a row carries in a tournament's table.

A number is allocated once, when the row enters the tournament, and never
changes or is reissued afterwards — not on a deletion, a merge, a re-upload, or
a re-sort (spec etl-console, Fixed fencer number). Allocation happens where a
row is born, never while the sheet is read, so `GET /sheet` stays a read.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SheetRowNumber, Tournament


def numbers_for(session: Session, tournament: Tournament) -> dict[str, int]:
    """Every number allocated in this tournament, by sheet row id."""
    rows = session.scalars(
        select(SheetRowNumber).where(SheetRowNumber.tournament_id == tournament.id)
    ).all()
    return {row.row_id: row.number for row in rows}


def allocate(session: Session, tournament: Tournament, row_ids: list[str]) -> dict[str, int]:
    """Give each row id its number, in the order given, minting one only where
    none exists. Returns the numbers of all the ids asked about, allocated now
    or earlier."""
    existing = numbers_for(session, tournament)
    wanted = [row_id for row_id in row_ids if row_id not in existing]
    if not wanted:
        return {row_id: existing[row_id] for row_id in row_ids if row_id in existing}

    highest = session.scalar(
        select(func.max(SheetRowNumber.number)).where(
            SheetRowNumber.tournament_id == tournament.id
        )
    )
    # counts up from the highest ever allocated, never from the count of rows
    # now present, so a freed number is not handed to someone else
    next_number = (highest or 0) + 1
    for row_id in dict.fromkeys(wanted):
        session.add(
            SheetRowNumber(
                tournament_id=tournament.id, row_id=row_id, number=next_number
            )
        )
        existing[row_id] = next_number
        next_number += 1
    session.flush()
    return {row_id: existing[row_id] for row_id in row_ids if row_id in existing}


def restore(session: Session, tournament: Tournament, pairs: list[tuple[str, int]]) -> None:
    """Reinstate numbers exactly as an exported document recorded them, gaps
    and all. A restored tournament keeps the numbers its fencers were given;
    reallocating them would renumber everyone."""
    for row_id, number in pairs:
        session.add(
            SheetRowNumber(tournament_id=tournament.id, row_id=row_id, number=number)
        )
    session.flush()


def arrival_order(session: Session, tournament: Tournament) -> list[str]:
    """The order rows would have been numbered in, for a document that records
    no numbers: registrations by registration moment, then the latest imported
    batch in file order, then the hand-entered rows as they were entered."""
    from app import importer
    from app.models import ImportedRow, ManualRow, Registration

    row_ids = [
        f"reg:{row_id}"
        for row_id in session.scalars(
            select(Registration.id)
            .where(Registration.tournament_id == tournament.id)
            .order_by(Registration.registered_at, Registration.id)
        )
    ]
    batch = importer.latest_batch(session, tournament)
    if batch is not None:
        row_ids += [
            f"imp:{key}"
            for key in session.scalars(
                select(ImportedRow.key)
                .where(ImportedRow.batch_id == batch.id)
                .order_by(ImportedRow.row_number)
            )
        ]
    row_ids += [
        f"man:{row_id}"
        for row_id in session.scalars(
            select(ManualRow.id)
            .where(ManualRow.tournament_id == tournament.id)
            .order_by(ManualRow.id)
        )
    ]
    return row_ids
