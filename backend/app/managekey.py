"""The manage key of a guest registration (spec `guest-registration`, design D4).

Derived, not stored. A message about a guest registration must carry its link
whenever it is sent — the scheduler's reminder runs days after the registration
was made — so the key has to be producible again at will. A stored random token
could only be mailed once, by whoever generated it; storing it in plaintext
would make the column a password column. An HMAC over the registration's id and
its `manage_key_generation` is producible at will, revocable by incrementing the
generation, and holds no secret in the database.

Rotating `settings.secret_key` kills every manage link, as it kills every
session token.
"""

import base64
import hashlib
import hmac

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Registration

# 32 base64 characters: 192 bits of the MAC, far past guessing
_MAC_LENGTH = 32


def _mac(registration_id: int, generation: int) -> str:
    digest = hmac.new(
        settings.secret_key.encode(),
        f"manage|{registration_id}|{generation}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode()[:_MAC_LENGTH]


def key_for(registration: Registration) -> str | None:
    """The registration's current key, or `None` for one that is not a guest's."""
    generation = registration.manage_key_generation
    if generation is None:
        return None
    return f"{registration.id}.{_mac(registration.id, generation)}"


def resolve(session: Session, key: str) -> Registration | None:
    """The registration a key names, where the key is its current one.

    A key naming no registration, one naming a registration that is not a
    guest's, and one carrying a superseded generation all come back as `None`,
    so the caller cannot refuse them differently: a refusal must not tell its
    reader which registrations exist."""
    head, _, mac = key.partition(".")
    if not head.isdigit() or len(mac) != _MAC_LENGTH:
        return None
    registration = session.get(Registration, int(head))
    # compared even when there is nothing to compare against, so the answer
    # takes the same time either way
    generation = registration.manage_key_generation if registration is not None else None
    expected = _mac(int(head), generation if generation is not None else -1)
    if not hmac.compare_digest(expected, mac) or generation is None:
        return None
    return registration


def rotate(registration: Registration) -> None:
    """Kill every link mailed so far and make a new one current. A registration
    that is not a guest's has no link to rotate."""
    if registration.manage_key_generation is not None:
        registration.manage_key_generation += 1
