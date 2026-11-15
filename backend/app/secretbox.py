"""Sealing the bank feed token at rest (spec tournament-admin, A feed token is
kept encrypted).

A Fio token, even a read-only one, opens the whole history of the account it
reads, and every copy of the database would otherwise hold it: the server's
disk, the replica and its snapshots, a restore drill's copy. So it is stored
sealed under `settings.fio_token_key`, which lives in the deployment's
configuration and never in the database.

This is the only module that reads the key (design encrypt-fio-token D1).
Fernet is authenticated, so a value the key does not open is told apart from
one it does rather than decrypting into garbage.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet(key: str) -> Fernet | None:
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except ValueError:
        # a key that is not one: the deployment holds no usable key, which is
        # the same thing as holding none
        return None


def can_seal() -> bool:
    """Whether this deployment can keep a feed token at all."""
    return _fernet(settings.fio_token_key) is not None


def seal(token: str) -> str:
    """The token as it is stored. Raises where there is no key: a token is never
    stored readable as a fallback, so the caller asks `can_seal` first."""
    fernet = _fernet(settings.fio_token_key)
    if fernet is None:
        raise RuntimeError("HEMA_SQUIRE_FIO_TOKEN_KEY is not set; a feed token cannot be stored")
    return fernet.encrypt(token.encode()).decode()


def open_(stored: str) -> str | None:
    """The token a stored value seals, or `None` where the key does not open it:
    lost, replaced, or never set. Unreadable is a state the caller reports, not
    an error (design D3)."""
    fernet = _fernet(settings.fio_token_key)
    if fernet is None:
        return None
    try:
        return fernet.decrypt(stored.encode()).decode()
    except InvalidToken:
        return None
