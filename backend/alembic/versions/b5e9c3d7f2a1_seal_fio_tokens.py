"""seal fio tokens

Revision ID: b5e9c3d7f2a1
Revises: a4d8f2c6e1b9
Create Date: 2026-11-15 23:00:00.000000

A bank feed token was stored as the token itself, so every copy of the
database held it readable: the server's disk, the replica and its snapshots,
any restore drill's copy (change encrypt-fio-token). This widens the column to
hold a Fernet value and seals every token already stored under
`HEMA_SQUIRE_FIO_TOKEN_KEY`.

A value that is already a Fernet token is left alone, whether or not it opens
under the key, so the revision can be run again and never seals a value
twice. Where a readable token is stored and no usable key is configured
the revision refuses, and the deploy fails with the old containers still
running, rather than leaving the tokens readable or dropping them (design D4).

The key is read through the application's settings, as env.py reads the
database URL, so a key in `.env` counts as one in the environment. Fernet is
used directly rather than through `app.secretbox`, so this revision keeps
meaning what it means when that module changes.

Downgrade opens each token back to plain text under the same key. One the key
does not open is unreadable under either schema and is cleared, so the old
code is not handed ciphertext to send to the bank as a token.
"""

import base64
import binascii
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = "b5e9c3d7f2a1"
down_revision: str | Sequence[str] | None = "a4d8f2c6e1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_tournaments = sa.table(
    "tournaments", sa.column("id", sa.Integer), sa.column("fio_token", sa.String)
)


def _fernet() -> Fernet | None:
    try:
        return Fernet(settings.fio_token_key.encode()) if settings.fio_token_key else None
    except ValueError:
        return None


def _sealed(value: str) -> bool:
    """Whether a value is a Fernet token at all, under whatever key. One sealed
    under a key since replaced does not open, and sealing it again would make
    it open into its own ciphertext, which would then pass for a token."""
    try:
        raw = base64.urlsafe_b64decode(value.encode())
    except binascii.Error, ValueError:
        return False
    # version byte, timestamp, IV, at least one cipher block, HMAC
    return len(raw) >= 1 + 8 + 16 + 16 + 32 and raw[0] == 0x80


def _stored(conn: sa.Connection) -> list[tuple[int, str]]:
    rows = conn.execute(
        sa.select(_tournaments.c.id, _tournaments.c.fio_token).where(
            _tournaments.c.fio_token.is_not(None), _tournaments.c.fio_token != ""
        )
    ).all()
    return [(row.id, row.fio_token) for row in rows]


def _refuse() -> None:
    raise RuntimeError(
        "tournaments hold Fio tokens that this revision must seal, and no usable "
        "HEMA_SQUIRE_FIO_TOKEN_KEY is configured. Generate one with "
        '`python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"`, put it in deploy/.env and the '
        "password manager, and run the migration again."
    )


def upgrade() -> None:
    conn = op.get_bind()
    fernet = _fernet()
    plain = [(id_, value) for id_, value in _stored(conn) if not _sealed(value)]
    # before any DDL: SQLite runs this revision outside a transaction, so a
    # refusal after the widening would leave the schema half-moved
    if plain and fernet is None:
        _refuse()
        return
    with op.batch_alter_table("tournaments") as batch:
        batch.alter_column(
            "fio_token", existing_type=sa.String(length=200), type_=sa.String(length=400)
        )
    if fernet is None:
        return
    for id_, value in plain:
        conn.execute(
            _tournaments.update()
            .where(_tournaments.c.id == id_)
            .values(fio_token=fernet.encrypt(value.encode()).decode())
        )


def downgrade() -> None:
    conn = op.get_bind()
    fernet = _fernet()
    stored = _stored(conn)
    if stored and fernet is None:
        _refuse()
        return
    for id_, value in stored:
        opened: str | None = None
        if fernet is not None:
            try:
                opened = fernet.decrypt(value.encode()).decode()
            except InvalidToken:
                opened = None
        conn.execute(_tournaments.update().where(_tournaments.c.id == id_).values(fio_token=opened))
    with op.batch_alter_table("tournaments") as batch:
        batch.alter_column(
            "fio_token", existing_type=sa.String(length=400), type_=sa.String(length=200)
        )
