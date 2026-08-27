"""Confirms the design's central safety claim for newly-bounded fields
(design `add-field-validation`, Risks / task 8.4): a bound applies only to
what a request submits, so a row that predates the bound keeps rendering and
is not silently rejected on an unrelated read or edit.

Tournament-level fields (`TournamentUpdate` uses `exclude_unset=True` partial
patch semantics) are only re-validated when the request actually includes
them. Discipline-level fields are re-validated on every save of that row,
since the Setup discipline table resubmits the whole object each time (task
0.1/0.3) — the row still renders, and only *that row's next save* is
blocked, not reads."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Discipline, Tournament


def _make_tournament(client, headers, slug="cup"):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_over_long_tournament_description_still_renders_and_only_blocks_its_own_field(
    client, auth_headers, engine
):
    headers = auth_headers()
    _make_tournament(client, headers)
    over_long = "x" * 6000
    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        tournament.description = over_long
        session.commit()

    detail = client.get("/api/tournaments/cup", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["description"] == over_long

    # an unrelated field can still be saved without touching description
    unrelated = client.patch("/api/tournaments/cup", json={"location": "Prague"}, headers=headers)
    assert unrelated.status_code == 200

    # only resubmitting the offending field itself is rejected
    blocked = client.patch(
        "/api/tournaments/cup", json={"description": over_long}, headers=headers
    )
    assert blocked.status_code == 422


def test_over_long_discipline_field_still_renders_but_blocks_the_rows_next_save(
    client, auth_headers, engine
):
    headers = auth_headers()
    _make_tournament(client, headers)
    created = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 10, "fee": 800},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]
    over_long_where = "Main Hall, " + "x" * 400
    with Session(engine) as session:
        discipline = session.scalar(select(Discipline).where(Discipline.slug == slug))
        discipline.schedule_where = over_long_where
        session.commit()

    detail = client.get("/api/tournaments/cup", headers=headers)
    assert detail.status_code == 200
    row = next(d for d in detail.json()["disciplines"] if d["slug"] == slug)
    assert row["schedule_where"] == over_long_where

    # the Setup discipline table resubmits the whole row on every save (task
    # 0.1/0.3), so even an edit that does not touch schedule_where is blocked
    # until it is fixed
    blocked = client.patch(
        f"/api/tournaments/cup/disciplines/{slug}",
        json={
            "weapon": "LS", "capacity": 12, "fee": 800,
            "schedule_where": over_long_where,
        },
        headers=headers,
    )
    assert blocked.status_code == 422
