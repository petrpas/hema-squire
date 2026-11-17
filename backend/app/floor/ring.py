"""The piste screen's keys and its current work (spec floor-ring; design
add-floor-pools D5).

A key covers one piste of one tournament. It travels in the address's
fragment and an `X-Floor-Ring-Key` header, and is stored as its SHA-256 hash.
Issuing a new key revokes the piste's previous one.
"""

import hashlib
import io
import secrets
from datetime import UTC, datetime

import qrcode
from qrcode.image.pil import PilImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.floor.models import FloorBout, FloorDraw, FloorPiste, FloorPool, FloorRingKey
from app.floor.pools import members_of


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def live_key(session: Session, tid: int, piste: int) -> FloorRingKey | None:
    return session.scalar(
        select(FloorRingKey).where(
            FloorRingKey.tournament_id == tid,
            FloorRingKey.piste_id == piste,
            FloorRingKey.revoked_at.is_(None),
        )
    )


def issue(session: Session, tid: int, piste: int, now: datetime) -> str:
    """A fresh key for the piste; the previous one stops working."""
    revoke(session, tid, piste, now)
    key = secrets.token_urlsafe(24)
    session.add(FloorRingKey(tournament_id=tid, piste_id=piste, key_hash=_hash(key), issued_at=now))
    session.flush()
    return key


def revoke(session: Session, tid: int, piste: int, now: datetime) -> None:
    current = live_key(session, tid, piste)
    if current is not None:
        current.revoked_at = now
        session.flush()


def resolve(session: Session, key: str) -> FloorRingKey | None:
    """The live key a presented key is, or None."""
    return session.scalar(
        select(FloorRingKey).where(
            FloorRingKey.key_hash == _hash(key), FloorRingKey.revoked_at.is_(None)
        )
    )


def current_pool(session: Session, tid: int, piste: int) -> FloorPool | None:
    """The piste's earliest announced pool, of pools not yet closed, that still
    has a bout without a result (spec floor-ring)."""
    pools = session.scalars(
        select(FloorPool)
        .join(FloorDraw, FloorDraw.id == FloorPool.draw_id)
        .where(
            FloorDraw.tournament_id == tid,
            FloorDraw.announced_at.is_not(None),
            FloorDraw.closed_at.is_(None),
            FloorPool.piste_id == piste,
        )
    ).all()
    open_pools = [
        p
        for p in pools
        if session.scalar(
            select(FloorBout.id).where(FloorBout.pool_id == p.id, FloorBout.recorded_at.is_(None))
        )
        is not None
    ]
    if not open_pools:
        return None
    return min(open_pools, key=lambda p: (_when(p), p.id))


def _when(pool: FloorPool) -> datetime:
    """A pool's planned start, aware; a pool without one sorts last."""
    start = pool.planned_start
    if start is None:
        return datetime.max.replace(tzinfo=UTC)
    return start if start.tzinfo is not None else start.replace(tzinfo=UTC)


def work(session: Session, key: FloorRingKey, names: dict[str, str]) -> dict[str, object]:
    """What the piste screen shows: the piste, and its current pool's bouts."""
    piste = session.get(FloorPiste, key.piste_id)
    pool = current_pool(session, key.tournament_id, key.piste_id)
    if pool is None:
        return {"piste": piste.name if piste else "", "pool": None}
    draw = session.get(FloorDraw, pool.draw_id)
    bouts = session.scalars(
        select(FloorBout).where(FloorBout.pool_id == pool.id).order_by(FloorBout.ordinal)
    ).all()
    return {
        "piste": piste.name if piste else "",
        "pool": {
            "discipline_id": draw.discipline_id if draw else None,
            "number": pool.number,
            "members": [
                {"key": m.entrant_key, "name": names.get(m.entrant_key, m.entrant_key)}
                for m in members_of(session, pool)
            ],
            "bouts": [
                {
                    "id": b.id,
                    "ordinal": b.ordinal,
                    "a": names.get(b.a_key, b.a_key),
                    "b": names.get(b.b_key, b.b_key),
                    "score_a": b.score_a,
                    "score_b": b.score_b,
                    "outcome_a": b.outcome_a,
                    "outcome_b": b.outcome_b,
                    "version": b.version,
                }
                for b in bouts
            ],
        },
    }


def qr_png(text: str) -> bytes:
    """A QR code of the piste screen's link, as PNG."""
    image = qrcode.make(text, image_factory=PilImage)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()
