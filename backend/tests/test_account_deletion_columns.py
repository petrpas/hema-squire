"""Every text-bearing column is placed in the deletion map (design
account-deletion D9): a new column holding a name or an address cannot be
added without someone deciding what a deletion does to it."""

import sqlalchemy as sa

from app.account_deletion import COLUMN_HANDLING
from app.models import Base

HANDLINGS = {"removed", "redacted", "kept", "none"}


def _text_columns() -> set[str]:
    return {
        f"{table.name}.{column.name}"
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, sa.String | sa.Text | sa.JSON)
    }


def test_every_text_column_is_classified():
    missing = _text_columns() - COLUMN_HANDLING.keys()
    assert not missing, f"classify in account_deletion.COLUMN_HANDLING: {sorted(missing)}"


def test_the_map_names_no_column_that_is_gone():
    stale = COLUMN_HANDLING.keys() - _text_columns()
    assert not stale, f"no longer in the schema: {sorted(stale)}"


def test_every_entry_has_a_handling_and_a_reason():
    for name, (handling, reason) in COLUMN_HANDLING.items():
        assert handling in HANDLINGS, name
        assert reason, name
