"""The pools' HTTP surface (specs floor-draw, floor-pools, floor-ring).

Console endpoints stand behind the console gate, writes refused on a draft;
the piste screen's two endpoints stand behind its key alone, rate-limited.
"""

import base64
from datetime import UTC, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select

from app.auth import require_console_access, require_published
from app.floor import bracket, officiating, people, poolbouts, pools, results, ring, sheets
from app.floor.adapters.office import (
    FencerDep,
    SessionDep,
    TournamentDep,
    has_floor,
    limiter,
    setup_facts,
)
from app.floor.datasheet import roster, roster_of
from app.floor.models import FloorBout, FloorFormat, FloorPiste, FloorPool, FloorRingKey
from app.floor.roster import FloorDiscipline
from app.floor.schemas import RowId
from app.floor.setup import read_pistes, team_total

router = APIRouter(prefix="/api/tournaments", tags=["floor"])
ring_router = APIRouter(prefix="/api/floor/ring", tags=["floor"])

Score = Annotated[int, Field(ge=0, le=99)]
Outcome = Annotated[str, StringConstraints(pattern="^(win|loss|draw|no)$")]


class ResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_a: Score
    score_b: Score
    outcome_a: Outcome
    outcome_b: Outcome
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    # the version read; a stale one is refused
    version: Annotated[int, Field(ge=0, le=1_000_000)]


class SheetBoutIn(ResultIn):
    id: RowId


class SheetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bouts: list[SheetBoutIn]


class SwapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    b: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class KeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # the console's own origin, which the link and its QR code are built on
    origin: Annotated[str, StringConstraints(pattern=r"^https?://[^/#?\s]{1,200}$")]


class KeyOut(BaseModel):
    key: str
    # the piste screen's address, the key in its fragment, as a PNG QR code
    qr_png_base64: str


def _discipline(tournament: TournamentDep, discipline_id: int) -> FloorDiscipline:
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    found = next((d for d in setup_facts(tournament).disciplines if d.id == discipline_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    return found


def _refused(error: pools.Refused) -> HTTPException:
    if error.detail is not None:
        return HTTPException(status_code=409, detail={"reason": error.code, "items": error.detail})
    status = 404 if error.code.endswith("_not_found") else 409
    return HTTPException(status_code=status, detail=error.code)


def _result(data: ResultIn) -> poolbouts.Result:
    return poolbouts.Result(
        score_a=data.score_a,
        score_b=data.score_b,
        outcome_a=data.outcome_a,
        outcome_b=data.outcome_b,
        note=data.note,
    )


@router.get("/{slug}/floor/pools/{discipline_id}")
def floor_pools(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, object]:
    """The discipline's draw or pools in their state, with standings, warnings
    and the call list."""
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    tid = tournament.id
    names = {
        k: p.name for k, p in people.persons(session, tid, roster(session, tournament)).items()
    }
    draw = pools.draw_of(session, tid, discipline.id)
    out: dict[str, object] = {
        "state": poolbouts.state(session, tid, discipline.id),
        "checkin_closed": people.snapshot(session, tid, discipline.id) is not None,
        "names": names,
        "draw": None,
    }
    if draw is None:
        return out
    bouts = pools.bouts_of(session, tid, discipline.id)
    out["draw"] = {
        "score": draw.score,
        "previous_score": draw.previous_score,
        "announced_at": draw.announced_at,
        "closed_at": draw.closed_at,
        "pools": [
            {
                "number": pool.number,
                "wave": pool.wave,
                "piste_id": pool.piste_id,
                "planned_start": pool.planned_start,
                "members": [
                    {"key": m.entrant_key, "seed": m.seed} for m in pools.members_of(session, pool)
                ],
                "bouts": [
                    {
                        "id": b.id,
                        "ordinal": b.ordinal,
                        "a": b.a_key,
                        "b": b.b_key,
                        "score_a": b.score_a,
                        "score_b": b.score_b,
                        "outcome_a": b.outcome_a,
                        "outcome_b": b.outcome_b,
                        "note": b.note,
                        "recorded_by": b.recorded_by,
                        "version": b.version,
                    }
                    for b in bouts
                    if b.pool_id == pool.id
                ],
            }
            for pool in pools.pools_of(session, draw)
        ],
    }
    out["standings"] = poolbouts.standings(session, tid, discipline.id)
    out["call_list"] = poolbouts.call_list(session, tid, discipline.id)
    return out


def _write(tournament: TournamentDep, discipline_id: int) -> FloorDiscipline:
    discipline = _discipline(tournament, discipline_id)
    require_published(tournament)
    return discipline


@router.post("/{slug}/floor/pools/{discipline_id}/draw", status_code=204)
def floor_draw(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """Draw, or draw again with a new random seed, before announcing."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        pools.make(session, tournament.id, roster(session, tournament), discipline)
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/pools/{discipline_id}/swap", status_code=204)
def floor_swap(
    discipline_id: RowId,
    data: SwapIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        pools.swap(session, tournament.id, roster(session, tournament), discipline, data.a, data.b)
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/pools/{discipline_id}/announce", status_code=204)
def floor_announce(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """ "Vyhlásit los": freezes the pools and pins them for the planner."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        pools.announce(session, tournament.id, discipline, fencer.id, datetime.now(UTC))
    except pools.Refused as error:
        raise _refused(error) from None
    # the draw reveals clubs and who fences where: officials are assigned again
    officiating.run(
        session, setup_facts(tournament), roster(session, tournament), datetime.now(UTC)
    )
    session.commit()


@router.get("/{slug}/floor/pools/{discipline_id}/reopen")
def floor_draw_reopen_preview(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, list[str]]:
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    return pools.reopen_preview(session, tournament.id, discipline.id)


@router.post("/{slug}/floor/pools/{discipline_id}/reopen", status_code=204)
def floor_draw_reopen(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        pools.reopen(session, tournament.id, discipline.id)
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.put("/{slug}/floor/pools/bouts/{bout_id}", status_code=204)
def floor_record_bout(
    bout_id: RowId,
    data: ResultIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    """Record or correct one bout; a stale version answers 409."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)
    try:
        poolbouts.record(
            session,
            tournament.id,
            bout_id,
            _result(data),
            data.version,
            f"user:{fencer.id}",
            datetime.now(UTC),
        )
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.put("/{slug}/floor/pools/{discipline_id}/sheet", status_code=204)
def floor_transcribe(
    discipline_id: RowId,
    data: SheetIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    """A whole paper sheet at once: every bout or none."""
    require_console_access(session, tournament, fencer)
    _write(tournament, discipline_id)
    now = datetime.now(UTC)
    try:
        for bout in data.bouts:
            poolbouts.record(
                session,
                tournament.id,
                bout.id,
                _result(bout),
                bout.version,
                f"user:{fencer.id}",
                now,
            )
    except pools.Refused as error:
        session.rollback()
        raise _refused(error) from None
    session.commit()


@router.get("/{slug}/floor/pools/{discipline_id}/close")
def floor_pools_close_preview(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, object]:
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    return poolbouts.close_preview(session, tournament.id, discipline.id)


@router.post("/{slug}/floor/pools/{discipline_id}/close", status_code=204)
def floor_pools_close(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """ "Uzavřít skupiny": freezes the ranking that seeds the elimination."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        poolbouts.close(session, tournament.id, discipline.id, fencer.id, datetime.now(UTC))
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/pools/{discipline_id}/reopen-pools", status_code=204)
def floor_pools_reopen(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        poolbouts.reopen(session, tournament.id, discipline.id)
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


def _format_of(session: SessionDep, discipline: FloorDiscipline) -> FloorFormat | None:
    return session.scalar(select(FloorFormat).where(FloorFormat.discipline_id == discipline.id))


def _pool_heading(
    session: SessionDep, tournament: TournamentDep, discipline: FloorDiscipline, pool: FloorPool
) -> str:
    """The discipline line of a pool sheet: with its piste and planned start
    where a schedule is planned, and the point target where stated (spec
    floor-pools, Pool sheets list the bouts in order)."""
    parts = [discipline.name]
    if pool.piste_id is not None:
        names = {p.id: p.name for p in read_pistes(session, tournament.id)}
        parts.append(f"planš {names.get(pool.piste_id, '')}".strip())
    if pool.planned_start is not None:
        moment = pool.planned_start
        aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
        zone = ZoneInfo(setup_facts(tournament).timezone)
        parts.append(aware.astimezone(zone).strftime("%H:%M"))
    fmt = _format_of(session, discipline)
    if fmt is not None and fmt.points_pool is not None:
        parts.append(f"do {fmt.points_pool} bodů")
    return " · ".join(parts)


def _bracket_heading(session: SessionDep, discipline: FloorDiscipline) -> str:
    """The discipline line of a bracket sheet, with its point targets: the
    elimination's and the final's, a team's per bout with the match total."""
    fmt = _format_of(session, discipline)
    if fmt is None:
        return discipline.name
    parts = [discipline.name]
    if discipline.kind == "team":
        for label, points in (
            ("eliminace", fmt.points_team_bout),
            ("finále", fmt.points_team_final),
        ):
            if points is not None:
                total = team_total(points, discipline.team_min)
                parts.append(f"{label} {points} bodů na střet, celkem do {total}")
    else:
        for label, points in (("eliminace", fmt.points_elim), ("finále", fmt.points_final)):
            if points is not None:
                parts.append(f"{label} do {points} bodů")
    return " · ".join(parts)


@router.get("/{slug}/floor/pools/{discipline_id}/sheets/{number}")
def floor_pool_sheet(
    discipline_id: RowId,
    number: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> Response:
    """One pool's sheet as PDF, from the adopted template."""
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    draw = pools.draw_of(session, tournament.id, discipline.id)
    pool = (
        next((p for p in pools.pools_of(session, draw) if p.number == number), None)
        if draw
        else None
    )
    if draw is None or draw.announced_at is None or pool is None:
        raise HTTPException(status_code=404, detail="pool_not_found")
    known = people.persons(session, tournament.id, roster(session, tournament))
    names = [
        known[m.entrant_key].name if m.entrant_key in known else m.entrant_key
        for m in pools.members_of(session, pool)
    ]
    try:
        pdf = sheets.pool_sheet(
            tournament.display_name,
            _pool_heading(session, tournament, discipline, pool),
            number,
            names,
        )
    except sheets.NoTemplate:
        raise HTTPException(status_code=409, detail="no_template") from None
    return Response(content=pdf, media_type="application/pdf")


# ------------------------------------------------------------ piste keys


@router.get("/{slug}/floor/ring")
def floor_ring_keys(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> list[dict[str, object]]:
    """Each piste and whether a live key is out for it; never the key."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    out: list[dict[str, object]] = []
    for piste in read_pistes(session, tournament.id):
        if piste.id is None:
            continue
        key = ring.live_key(session, tournament.id, piste.id)
        out.append(
            {"piste_id": piste.id, "name": piste.name, "issued_at": key.issued_at if key else None}
        )
    return out


def _piste(session: SessionDep, tournament: TournamentDep, piste_id: int) -> None:
    piste = session.get(FloorPiste, piste_id)
    if piste is None or piste.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="piste_not_found")


@router.post("/{slug}/floor/ring/{piste_id}", response_model=KeyOut, status_code=201)
def floor_ring_issue(
    piste_id: RowId,
    data: KeyIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> KeyOut:
    """A fresh key for the piste's screen; the previous one stops working.
    The key is shown once, here."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)
    _piste(session, tournament, piste_id)
    key = ring.issue(session, tournament.id, piste_id, datetime.now(UTC))
    session.commit()
    link = f"{data.origin}/floor/ring/{piste_id}#{key}"
    return KeyOut(key=key, qr_png_base64=base64.b64encode(ring.qr_png(link)).decode("ascii"))


@router.delete("/{slug}/floor/ring/{piste_id}", status_code=204)
def floor_ring_revoke(
    piste_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    _piste(session, tournament, piste_id)
    ring.revoke(session, tournament.id, piste_id, datetime.now(UTC))
    session.commit()


# ------------------------------------------------------------ the piste screen


RingKey = Annotated[str, Header(alias="X-Floor-Ring-Key", min_length=8, max_length=128)]


def _resolve(session: SessionDep, key: str) -> FloorRingKey:
    found = ring.resolve(session, key)
    if found is None:
        raise HTTPException(status_code=404, detail="ring_key_invalid")
    return found


@ring_router.get("/current")
@limiter.limit("120/minute")
def ring_current(
    request: Request, session: SessionDep, x_floor_ring_key: RingKey
) -> dict[str, object]:
    """The piste's current pool, by the key in the header alone."""
    key = _resolve(session, x_floor_ring_key)
    found = roster_of(session, key.tournament_id)
    names = (
        {k: p.name for k, p in people.persons(session, key.tournament_id, found).items()}
        if found is not None
        else {}
    )
    return ring.work(session, key, names)


@ring_router.put("/bouts/{bout_id}", status_code=204)
@limiter.limit("60/minute")
def ring_record(
    request: Request,
    bout_id: RowId,
    data: ResultIn,
    session: SessionDep,
    x_floor_ring_key: RingKey,
) -> None:
    """Record a bout of the piste's own pool; attributed to `ring:<piste>`."""
    key = _resolve(session, x_floor_ring_key)
    bout = session.get(FloorBout, bout_id)
    try:
        if bout is not None and bout.bracket_id is not None:
            found = roster_of(session, key.tournament_id)
            discipline = (
                next((d for d in found.disciplines if d.id == bout.discipline_id), None)
                if found is not None
                else None
            )
            if discipline is None:
                raise pools.Refused("bout_not_found")
            bracket.record(
                session,
                key.tournament_id,
                bout_id,
                _result(data),
                data.version,
                f"ring:{key.piste_id}",
                datetime.now(UTC),
                discipline,
                piste=key.piste_id,
            )
        else:
            poolbouts.record(
                session,
                key.tournament_id,
                bout_id,
                _result(data),
                data.version,
                f"ring:{key.piste_id}",
                datetime.now(UTC),
                piste=key.piste_id,
            )
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


# ------------------------------------------------------------ the bracket
# (spec floor-bracket)


@router.get("/{slug}/floor/bracket/{discipline_id}")
def floor_bracket(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, object]:
    """The bracket in its state: the proposal before confirming, then its
    slots and bouts."""
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    tid = tournament.id
    found = roster(session, tournament)
    names = {k: p.name for k, p in people.persons(session, tid, found).items()}
    names.update({t.key: t.name for t in found.teams})
    # a discipline that takes over waits on its source's pools
    source = bracket.source_of(session, discipline.id)
    out: dict[str, object] = {
        "state": bracket.state(session, tid, discipline.id),
        "pools_closed": poolbouts.state(session, tid, source or discipline.id) == "closed",
        "source": source,
        "names": names,
        "proposal": None,
        "bracket": None,
    }
    row = bracket.bracket_of(session, tid, discipline.id)
    if row is None:
        if out["pools_closed"]:
            try:
                out["proposal"] = bracket.propose(session, tid, found, discipline)
            except pools.Refused:
                out["proposal"] = None
        return out
    out["bracket"] = {
        "size": row.size,
        "advancing": row.advancing,
        "third_place": row.third_place,
        "closed_at": row.closed_at,
        "slots": [
            {
                "round": s.round,
                "position": s.position,
                "key": s.entrant_key,
                "seed": s.seed,
                "bye": s.bye,
            }
            for s in sorted(
                bracket.slots_of(session, row).values(), key=lambda s: (s.round, s.position)
            )
        ],
        "bouts": [
            {
                "id": b.id,
                "round": b.round,
                "position": b.position,
                "a": b.a_key,
                "b": b.b_key,
                "score_a": b.score_a,
                "score_b": b.score_b,
                "outcome_a": b.outcome_a,
                "outcome_b": b.outcome_b,
                "note": b.note,
                "piste_id": b.piste_id,
                "version": b.version,
            }
            for b in bracket.bouts_of(session, row)
        ],
    }
    return out


@router.post("/{slug}/floor/bracket/{discipline_id}/confirm", status_code=204)
def floor_bracket_confirm(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """ "Potvrdit postup": freezes the seeded bracket."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        bracket.confirm(
            session,
            tournament.id,
            roster(session, tournament),
            discipline,
            fencer.id,
            datetime.now(UTC),
        )
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/bracket/{discipline_id}/reopen", status_code=204)
def floor_bracket_reopen(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        bracket.reopen(session, tournament.id, discipline.id)
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.put("/{slug}/floor/bracket/{discipline_id}/bouts/{bout_id}", status_code=204)
def floor_bracket_record(
    discipline_id: RowId,
    bout_id: RowId,
    data: ResultIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    """Record or correct an elimination bout; its winner advances."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        bracket.record(
            session,
            tournament.id,
            bout_id,
            _result(data),
            data.version,
            f"user:{fencer.id}",
            datetime.now(UTC),
            discipline,
        )
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.get("/{slug}/floor/bracket/{discipline_id}/sheet")
def floor_bracket_sheet(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> Response:
    """The bracket as PDF, as recorded so far."""
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    row = bracket.bracket_of(session, tournament.id, discipline.id)
    if row is None:
        raise HTTPException(status_code=404, detail="bracket_not_found")
    found = roster(session, tournament)
    names = {k: p.name for k, p in people.persons(session, tournament.id, found).items()}
    names.update({t.key: t.name for t in found.teams})
    slots = bracket.slots_of(session, row)
    by_seed: list[str | None] = [None] * row.size
    for (round_, _), slot in slots.items():
        if round_ == 0 and slot.seed is not None and slot.entrant_key is not None:
            by_seed[slot.seed - 1] = names.get(slot.entrant_key, slot.entrant_key)
    advanced: list[list[str | None]] = []
    total = row.size.bit_length() - 1
    for round_ in range(1, total + 1):
        line: list[str | None] = []
        for position in range(row.size // 2**round_):
            slot = slots.get((round_, position))
            fed_by_bye = round_ == 1 and any(
                (s := slots.get((0, 2 * position + i))) is not None and s.bye for i in (0, 1)
            )
            key = slot.entrant_key if slot is not None and not fed_by_bye else None
            line.append(names.get(key, key) if key is not None else None)
        advanced.append(line)
    final = next(
        (b for b in bracket.bouts_of(session, row) if b.round == total - 1 and b.position == 0),
        None,
    )
    champion = bracket._winner(final)  # pyright: ignore[reportPrivateUsage]  # the module's own rule for who won
    advanced[-1] = [names.get(champion, champion) if champion is not None else None]
    try:
        pdf = sheets.bracket_sheet(
            tournament.display_name,
            _bracket_heading(session, discipline),
            row.size,
            by_seed,
            advanced,
        )
    except sheets.NoTemplate:
        raise HTTPException(status_code=409, detail="no_template") from None
    return Response(content=pdf, media_type="application/pdf")


# ------------------------------------------------------------ officials on blocks
# (spec floor-officials)


class SeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    official_id: RowId | None
    pinned: bool = False


class SeatSwapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: RowId
    b: RowId


def _officials_refused(error: officiating.Refused) -> HTTPException:
    status = 404 if error.code.endswith("_not_found") else 409
    return HTTPException(status_code=status, detail=error.code)


@router.get("/{slug}/floor/officials")
def floor_officials(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, object]:
    """Blocks × roles with names, the unfilled seats, club conflicts and pins
    whose block is gone."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    return officiating.view(session, setup_facts(tournament), roster(session, tournament))


@router.post("/{slug}/floor/officials/run", status_code=204)
def floor_officials_run(tournament: TournamentDep, session: SessionDep, fencer: FencerDep) -> None:
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)
    officiating.run(
        session, setup_facts(tournament), roster(session, tournament), datetime.now(UTC)
    )
    session.commit()


@router.put("/{slug}/floor/officials/seats/{seat_id}", status_code=204)
def floor_officials_seat(
    seat_id: RowId, data: SeatIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """Put an official on a seat, pinned or not; a hard rule refuses it."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)
    try:
        officiating.set_seat(
            session,
            setup_facts(tournament),
            roster(session, tournament),
            seat_id,
            data.official_id,
            data.pinned,
        )
    except officiating.Refused as error:
        raise _officials_refused(error) from None
    session.commit()


@router.post("/{slug}/floor/officials/swap", status_code=204)
def floor_officials_swap(
    data: SeatSwapIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)
    try:
        officiating.swap(
            session, setup_facts(tournament), roster(session, tournament), data.a, data.b
        )
    except officiating.Refused as error:
        raise _officials_refused(error) from None
    session.commit()


@router.get("/{slug}/floor/officials/print/{kind}/{subject_id}")
def floor_officials_print(
    kind: Annotated[str, StringConstraints(pattern="^(official|piste)$")],
    subject_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> Response:
    """An official's rozpis, or a piste's sheet, as PDF."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    pistes = {p.id: p.name for p in read_pistes(session, tournament.id) if p.id is not None}
    title, headers, rows = officiating.print_rows(
        session, setup_facts(tournament), roster(session, tournament), kind, subject_id, pistes
    )
    if not rows:
        raise HTTPException(status_code=404, detail="nothing_to_print")
    pdf = sheets.table_pdf(title, tournament.display_name, headers, rows)
    return Response(content=pdf, media_type="application/pdf")


# ------------------------------------------------------------ results
# (spec floor-results)


@router.get("/{slug}/floor/results")
def floor_results(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> list[dict[str, object]]:
    """Each discipline's final standing, where its bracket is closed, and
    whether it is public."""
    require_console_access(session, tournament, fencer)
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    found = roster(session, tournament)
    out: list[dict[str, object]] = []
    for discipline in setup_facts(tournament).disciplines:
        row = results.published(session, tournament.id, discipline.id)
        out.append(
            {
                "discipline_id": discipline.id,
                "slug": discipline.slug,
                "name": discipline.name,
                "standing": results.placed(session, tournament.id, found, discipline),
                "published_at": row.published_at if row is not None else None,
            }
        )
    return out


@router.post("/{slug}/floor/results/{discipline_id}/publish", status_code=204)
def floor_results_publish(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """ "Zveřejnit výsledky": the discipline's standing becomes public."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    try:
        results.publish(session, tournament.id, discipline.id, fencer.id, datetime.now(UTC))
    except pools.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.delete("/{slug}/floor/results/{discipline_id}/publish", status_code=204)
def floor_results_withdraw(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """Withdraws publication; the public page changes at once."""
    require_console_access(session, tournament, fencer)
    discipline = _write(tournament, discipline_id)
    results.withdraw(session, tournament.id, discipline.id)
    session.commit()


@router.get("/{slug}/floor/results/{discipline_id}/{fmt}")
def floor_results_export(
    discipline_id: RowId,
    fmt: Annotated[str, StringConstraints(pattern="^(csv|pdf)$")],
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> Response:
    """The standing and every bout as CSV, or the standing as PDF."""
    require_console_access(session, tournament, fencer)
    discipline = _discipline(tournament, discipline_id)
    found = roster(session, tournament)
    if fmt == "csv":
        return Response(
            content=results.csv_export(session, tournament.id, found, discipline),
            media_type="text/csv; charset=utf-8",
        )
    standing = results.placed(session, tournament.id, found, discipline)
    if standing is None:
        raise HTTPException(status_code=409, detail="bracket_open")
    pdf = sheets.table_pdf(
        discipline.name,
        tournament.display_name,
        ["Pořadí", "Jméno", "Klub", "Národnost"],
        [
            [str(r["place"]), str(r["name"]), str(r["club"] or ""), str(r["nationality"] or "")]
            for r in standing
        ],
    )
    return Response(content=pdf, media_type="application/pdf")
