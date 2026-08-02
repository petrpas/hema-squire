"""hemaratings.com synchronization: fighters index refresh and rating snapshots.

Drift policy (Decision 8): when a fetch parses to an implausible result the
previous data is kept and the refresh is logged rejected with diagnostics —
no self-healing, no silently degraded index. The HRFetcher protocol is the
network boundary; tests substitute canned HTML.
"""

import html as html_mod
import re
import time
from datetime import datetime
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.hr_index import HRRating, fold
from app.models import (
    DisciplineKind,
    HRFighter,
    HRIndexRefresh,
    HRRatingSnapshot,
    HRSnapshotRating,
    Tournament,
)

FIGHTERS_URL = "https://hemaratings.com/fighters/"
FIGHTER_DETAILS_URL = "https://hemaratings.com/fighters/details/{hr_id}/"

# A healthy index has ~19k fighters; a parse far below the previous count or
# this floor means the page format drifted, not that HEMA shrank overnight.
MIN_PLAUSIBLE_FIGHTERS = 1000
MIN_FRACTION_OF_PREVIOUS = 0.8

# v1's proven mapping: our discipline code -> substring of the HR category
# header. Steel-open codes share the "Mixed & Men's" categories; plastic codes
# have no HR category. Overridable per tournament via hr_category_map.
DEFAULT_CATEGORY_KEYWORDS: dict[str, str] = {
    "LS": "Mixed & Men's Steel Longsword",
    "LSM": "Mixed & Men's Steel Longsword",
    "LSW": "Women's Steel Longsword",
    "SA": "Mixed & Men's Steel Sabre",
    "SAM": "Mixed & Men's Steel Sabre",
    "SAW": "Women's Steel Sabre",
    "SB": "Mixed & Men's Steel Sword and Buckler",
    "SBM": "Mixed & Men's Steel Sword and Buckler",
    "SBW": "Women's Steel Sword and Buckler",
    "RD": "Mixed & Men's Steel Rapier & Dagger",
    "RDM": "Mixed & Men's Steel Rapier & Dagger",
    "RDW": "Women's Steel Rapier & Dagger",
    "RA": "Mixed & Men's Steel Single Rapier",
    "RAM": "Mixed & Men's Steel Single Rapier",
    "RAW": "Women's Steel Single Rapier",
}


class HRFetcher(Protocol):
    def fighters_page(self) -> str: ...

    def fighter_page(self, hr_id: int) -> str | None: ...


class HttpHRFetcher:
    """Real fetcher; paced to be polite to hemaratings.com."""

    def __init__(self, delay_seconds: float = 0.3):
        self._delay = delay_seconds

    def _get(self, url: str) -> str | None:
        import httpx

        time.sleep(self._delay)
        response = httpx.get(
            url,
            headers={"User-Agent": "HEMA-Squire/0.1 (tournament administration)"},
            timeout=60,
            follow_redirects=True,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.text

    def fighters_page(self) -> str:
        text = self._get(FIGHTERS_URL)
        assert text is not None
        return text

    def fighter_page(self, hr_id: int) -> str | None:
        return self._get(FIGHTER_DETAILS_URL.format(hr_id=hr_id))


def get_hr_fetcher() -> HRFetcher:
    return HttpHRFetcher(delay_seconds=settings.hr_fetch_delay_seconds)


_FIGHTER_ROW = re.compile(r'href="/fighters/details/(\d+)/">([^<]+)</a>', re.DOTALL)
_NATIONALITY = re.compile(r'data-search="([^"]+)"')
_CLUB = re.compile(r'href="/clubs/[^"]+/">([^<]+)</a>')


def parse_fighters_html(html: str) -> list[tuple[int, str, str, str]]:
    """Extract (hr_id, name, nationality, club) rows. Parsed row-by-row so an
    empty club cell never inherits the next fighter's club (v1 lesson)."""
    fighters = []
    for row in re.split(r"(?=<tr[\s>])", html):
        fighter = _FIGHTER_ROW.search(row)
        if not fighter:
            continue
        nationality = _NATIONALITY.search(row)
        club = _CLUB.search(row)
        fighters.append(
            (
                int(fighter.group(1)),
                html_mod.unescape(fighter.group(2)).strip(),
                html_mod.unescape(nationality.group(1)).strip() if nationality else "",
                html_mod.unescape(club.group(1)).strip() if club else "",
            )
        )
    return fighters


def refresh_fighters(session: Session, fetcher: HRFetcher) -> dict:
    """Fetch and replace the fighters index; on an implausible parse keep the
    previous index and log the rejection with diagnostics."""
    previous = session.scalar(select(HRFighter).limit(1))
    previous_count = (
        session.query(HRFighter).count() if previous is not None else 0
    )

    try:
        page = fetcher.fighters_page()
    except Exception as error:
        session.add(HRIndexRefresh(status="failed", detail={"error": str(error)}))
        session.commit()
        return {"status": "failed", "detail": {"error": str(error)}}

    fighters = parse_fighters_html(page)
    seen: set[int] = set()
    unique = []
    for fighter in fighters:
        if fighter[0] not in seen:
            seen.add(fighter[0])
            unique.append(fighter)

    diagnostics = {
        "fetched_chars": len(page),
        "parsed": len(unique),
        "previous": previous_count,
    }
    floor = max(MIN_PLAUSIBLE_FIGHTERS, int(previous_count * MIN_FRACTION_OF_PREVIOUS))
    if len(unique) < floor:
        diagnostics["reason"] = (
            f"parsed {len(unique)} fighters, plausibility floor is {floor} — "
            "source format drift suspected; previous index kept"
        )
        session.add(
            HRIndexRefresh(status="rejected", fighter_count=len(unique), detail=diagnostics)
        )
        session.commit()
        return {"status": "rejected", "detail": diagnostics}

    session.execute(delete(HRFighter))
    session.add_all(
        HRFighter(
            hr_id=hr_id,
            name=name,
            name_folded=fold(name),
            nationality=nationality or None,
            club=club or None,
        )
        for hr_id, name, nationality, club in unique
    )
    session.add(
        HRIndexRefresh(status="ok", fighter_count=len(unique), detail=diagnostics)
    )
    session.commit()
    return {"status": "ok", "fighters": len(unique)}


def ensure_index(session: Session, fetcher: HRFetcher) -> dict | None:
    """Populate the index when empty (fresh deployment); no-op otherwise."""
    if session.scalar(select(HRFighter).limit(1)) is not None:
        return None
    return refresh_fighters(session, fetcher)


def index_status(session: Session) -> dict:
    last = session.scalars(
        select(HRIndexRefresh).order_by(HRIndexRefresh.id.desc()).limit(1)
    ).first()
    return {
        "fighters": session.query(HRFighter).count(),
        "last_refresh": None
        if last is None
        else {
            "at": last.fetched_at,
            "status": last.status,
            "fighter_count": last.fighter_count,
            "detail": last.detail,
        },
    }


# --- ratings snapshots ------------------------------------------------------

_RATINGS_TABLE = re.compile(r"<h3>Ratings</h3>.*?<tbody>(.*?)</tbody>", re.DOTALL)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)


def parse_fighter_ratings(html: str) -> list[tuple[str, float | None, int | None]]:
    """Parse a fighter details page into (category header, rating, rank) rows.
    Columns: Category | Last competed | Rank (current) | Weighted Rating (current) | ...
    """
    table = _RATINGS_TABLE.search(html)
    if not table:
        return []
    rows = []
    for row in re.split(r"<tr[^>]*>", table.group(1)):
        cells = [
            html_mod.unescape(re.sub(r"<[^>]+>", "", cell)).strip()
            for cell in _CELL.findall(row)
        ]
        if len(cells) < 4 or not cells[0]:
            continue
        rank_match = re.search(r"(\d+)", cells[2])
        try:
            rating = float(cells[3])
        except ValueError:
            rating = None
        rows.append((cells[0], rating, int(rank_match.group(1)) if rank_match else None))
    return rows


def category_keyword(tournament: Tournament, code: str) -> str | None:
    override = tournament.hr_category_map or {}
    return override.get(code, DEFAULT_CATEGORY_KEYWORDS.get(code))


def take_snapshot(
    session: Session, tournament: Tournament, fetcher: HRFetcher, hr_ids: list[int]
) -> dict:
    """Fetch current ratings for the given fencers and store a dated snapshot.
    If every page parses to zero categories, the fetch is rejected as drift."""
    # team disciplines carry no HR rating category (design team-disciplines:
    # "Team disciplines carry no HR rating category")
    codes = [d.code for d in tournament.disciplines if d.kind == DisciplineKind.INDIVIDUAL]
    parsed_pages = 0
    pages_with_ratings = 0
    missing: list[int] = []
    collected: list[HRSnapshotRating] = []

    snapshot = HRRatingSnapshot(tournament_id=tournament.id, fencer_count=len(hr_ids))
    for hr_id in hr_ids:
        page = fetcher.fighter_page(hr_id)
        if page is None:
            missing.append(hr_id)
            continue
        parsed_pages += 1
        categories = parse_fighter_ratings(page)
        if categories:
            pages_with_ratings += 1
        for code in codes:
            keyword = category_keyword(tournament, code)
            if keyword is None:
                continue
            match = next(
                (c for c in categories if keyword.lower() in c[0].lower()), None
            )
            if match is not None:
                collected.append(
                    HRSnapshotRating(
                        snapshot=snapshot,
                        hr_id=hr_id,
                        discipline_code=code,
                        rating=match[1],
                        rank=match[2],
                    )
                )

    if parsed_pages > 0 and pages_with_ratings == 0:
        return {
            "status": "rejected",
            "detail": {
                "reason": "every fighter page parsed to zero rating categories — "
                "source format drift suspected; no snapshot stored",
                "pages": parsed_pages,
            },
        }

    session.add(snapshot)
    session.add_all(collected)
    session.commit()
    return {
        "status": "ok",
        "snapshot_id": snapshot.id,
        "taken_at": snapshot.taken_at,
        "fencers": len(hr_ids),
        "ratings": len(collected),
        "missing": missing,
    }


def latest_ratings(
    session: Session, tournament: Tournament
) -> tuple[datetime | None, dict[tuple[int, str], HRRating]]:
    """The latest snapshot's ratings as a (hr_id, code) lookup for exports."""
    snapshot = session.scalars(
        select(HRRatingSnapshot)
        .where(HRRatingSnapshot.tournament_id == tournament.id)
        .options(selectinload(HRRatingSnapshot.ratings))
        .order_by(HRRatingSnapshot.id.desc())
        .limit(1)
    ).first()
    if snapshot is None:
        return None, {}
    return snapshot.taken_at, {
        (r.hr_id, r.discipline_code): HRRating(rating=r.rating, rank=r.rank)
        for r in snapshot.ratings
    }
