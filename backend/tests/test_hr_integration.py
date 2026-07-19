"""Task 1.4 — fighters index: refresh, drift detection, DB-backed search,
rating snapshots with the per-tournament category mapping."""

import pytest

from app.db import get_session
from app.hr_index import get_hr_index
from app.hr_sync import get_hr_fetcher, parse_fighters_html
from app.main import app
from tests.test_sheets_export import FakeHRFetcher, fighter_page


def fighters_html(fighters: list[tuple[int, str, str, str]]) -> str:
    rows = []
    for hr_id, name, nationality, club in fighters:
        club_cell = f'<td><a href="/clubs/{hr_id}/">{club}</a></td>' if club else "<td></td>"
        rows.append(
            f'<tr><td><a href="/fighters/details/{hr_id}/">{name}</a></td>'
            f'<td data-search="{nationality}">flag</td>{club_cell}</tr>'
        )
    return f"<table><tbody>{''.join(rows)}</tbody></table>"


FIGHTERS = [
    (582, "Jan Nov&#225;k", "Czech Republic", "Prague HEMA"),
    (777, "Ond&#345;ej Malina", "Czech Republic", "Ro&#382;novsky &#353;ermirsky klub"),
    (901, "Clubless Fighter", "Poland", ""),
]


class IndexFetcher(FakeHRFetcher):
    def __init__(self, html: str):
        super().__init__()
        self.html = html
        self.calls = 0

    def fighters_page(self):
        self.calls += 1
        return self.html


@pytest.fixture
def use_real_index(client):
    """Switch from the conftest stub to the DB-backed index."""
    app.dependency_overrides.pop(get_hr_index, None)
    yield


@pytest.fixture(autouse=True)
def plausibility_floor(monkeypatch):
    """The real floor is 1000 fighters; tests work with a handful."""
    monkeypatch.setattr("app.hr_sync.MIN_PLAUSIBLE_FIGHTERS", 2)


def wire_fetcher(fetcher):
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher


def make_organizer(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizer_names": ["Cup Org"]},
        headers=organizer,
    )
    return organizer


def test_parse_fighters_html_handles_entities_and_empty_clubs():
    parsed = parse_fighters_html(fighters_html(FIGHTERS))
    assert parsed == [
        (582, "Jan Novák", "Czech Republic", "Prague HEMA"),
        (777, "Ondřej Malina", "Czech Republic", "Rožnovsky šermirsky klub"),
        (901, "Clubless Fighter", "Poland", ""),  # no club bleed from next row
    ]


def test_refresh_populates_index_and_search_folds_diacritics(
    client, auth_headers, use_real_index
):
    organizer = make_organizer(client, auth_headers)
    wire_fetcher(IndexFetcher(fighters_html(FIGHTERS)))

    outcome = client.post("/api/hr/refresh", headers=organizer)
    assert outcome.status_code == 200
    assert outcome.json() == {"status": "ok", "fighters": 3}

    # diacritics-insensitive search over the DB index
    results = client.get("/api/hr/search?q=ondrej", headers=organizer).json()
    assert [r["hr_id"] for r in results] == [777]
    assert results[0]["name"] == "Ondřej Malina"
    results = client.get("/api/hr/search?q=novák", headers=organizer).json()
    assert [r["hr_id"] for r in results] == [582]

    # newly registered fighters become findable after a refresh
    grown = FIGHTERS + [(1500, "New Fighter", "Slovakia", "Bratislava HEMA")]
    wire_fetcher(IndexFetcher(fighters_html(grown)))
    client.post("/api/hr/refresh", headers=organizer)
    results = client.get("/api/hr/search?q=new+fighter", headers=organizer).json()
    assert [r["hr_id"] for r in results][0] == 1500  # best similarity match ranks first

    status = client.get("/api/hr/status", headers=organizer).json()
    assert status["fighters"] == 4
    assert status["last_refresh"]["status"] == "ok"


def test_hr_binding_uses_db_index(client, auth_headers, use_real_index):
    organizer = make_organizer(client, auth_headers)
    wire_fetcher(IndexFetcher(fighters_html(FIGHTERS)))
    client.post("/api/hr/refresh", headers=organizer)

    fencer = auth_headers(email="jan@example.com", name="Jan N")
    binding = client.post(
        "/api/account/hr-binding", json={"hr_id": 582}, headers=fencer
    )
    assert binding.status_code == 200
    assert binding.json()["display_name"] == "Jan Novák"  # canonical HR name


def test_drift_rejected_keeps_previous_index(client, auth_headers, use_real_index):
    organizer = make_organizer(client, auth_headers)
    wire_fetcher(IndexFetcher(fighters_html(FIGHTERS)))
    client.post("/api/hr/refresh", headers=organizer)

    # the page format drifts: parse yields an implausibly small list
    wire_fetcher(IndexFetcher("<html>redesigned page, nothing parseable</html>"))
    response = client.post("/api/hr/refresh", headers=organizer)
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["status"] == "rejected"
    assert "drift" in detail["detail"]["reason"]
    assert detail["detail"]["previous"] == 3

    # previous index intact and searchable; rejection is logged for diagnostics
    results = client.get("/api/hr/search?q=ondrej", headers=organizer).json()
    assert [r["hr_id"] for r in results] == [777]
    status = client.get("/api/hr/status", headers=organizer).json()
    assert status["fighters"] == 3
    assert status["last_refresh"]["status"] == "rejected"


def test_refresh_requires_organizer(client, auth_headers, use_real_index):
    make_organizer(client, auth_headers)
    outsider = auth_headers(email="visitor@example.com", name="Visitor")
    wire_fetcher(IndexFetcher(fighters_html(FIGHTERS)))
    assert client.post("/api/hr/refresh", headers=outsider).status_code == 403


SIMILARITY_FIGHTERS = [
    (600, "Petr Pa&#353;&#269;enko", "Czech Republic", "Praha HEMA"),
    (601, "Pavel Pa&#353;ek", "Czech Republic", "Ostrava HEMA"),
    (602, "Karel Novotn&#253;", "Slovakia", "Bratislava HEMA"),
    (603, "Petr Sokol", "Czech Republic", "Sokol Brno"),
]


def test_search_ranks_by_similarity_and_nationality_narrows(
    client, auth_headers, use_real_index
):
    organizer = make_organizer(client, auth_headers)
    wire_fetcher(IndexFetcher(fighters_html(SIMILARITY_FIGHTERS)))
    client.post("/api/hr/refresh", headers=organizer)

    # no nationality: token prefilter admits both "Petr"s, similarity ranks
    # the true match ("pascenko") first
    results = client.get("/api/hr/search?q=petr+pascenko", headers=organizer).json()
    assert [r["hr_id"] for r in results][0] == 600
    assert {r["hr_id"] for r in results} == {600, 603}  # Karel/Pavel share no token

    # nationality narrows the candidate space; every row of that nationality
    # is scored and returned even without a strong match (D4: no threshold)
    results = client.get(
        "/api/hr/search?q=pascenko&nationality=Slovakia", headers=organizer
    ).json()
    assert [r["hr_id"] for r in results] == [602]

    results = client.get(
        "/api/hr/search?q=pascenko&nationality=Czech Republic", headers=organizer
    ).json()
    assert [r["hr_id"] for r in results][0] == 600
    assert {r["hr_id"] for r in results} == {600, 601, 603}


def test_hr_nationalities_lists_distinct_sorted_values(client, auth_headers, use_real_index):
    organizer = make_organizer(client, auth_headers)
    wire_fetcher(IndexFetcher(fighters_html(SIMILARITY_FIGHTERS)))
    client.post("/api/hr/refresh", headers=organizer)

    nationalities = client.get("/api/hr/nationalities", headers=organizer).json()
    assert nationalities == ["Czech Republic", "Slovakia"]


def test_snapshot_respects_category_mapping_and_override(client, auth_headers):
    organizer = make_organizer(client, auth_headers)
    for code in ("LS", "SAW"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"code": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    fencer = auth_headers(email="jan@example.com", name="Jan N")
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer)
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS", "SAW"]},
        headers=fencer,
    )

    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page(
        [
            ("Mixed & Men's Steel Longsword", 1400.0, 20),
            ("Women's Steel Sabre", 1200.0, 8),
            ("Historical Experimental Sabre", 999.0, 1),
        ]
    )
    wire_fetcher(fetcher)

    outcome = client.post(
        "/api/tournaments/cup/ratings/snapshot", headers=organizer
    ).json()
    assert outcome["status"] == "ok"
    assert outcome["fencers"] == 1
    assert outcome["ratings"] == 2  # LS and SAW via the default keyword table

    # per-tournament override: point SAW at the experimental category
    client.patch(
        "/api/tournaments/cup",
        json={"hr_category_map": {"SAW": "Historical Experimental Sabre"}},
        headers=organizer,
    )
    client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer)

    session = next(app.dependency_overrides[get_session]())
    from sqlalchemy import select

    from app.models import HRRatingSnapshot

    snapshot = session.scalars(
        select(HRRatingSnapshot).order_by(HRRatingSnapshot.id.desc()).limit(1)
    ).first()
    by_code = {r.discipline_code: r for r in snapshot.ratings}
    assert by_code["SAW"].rating == 999.0
    assert by_code["LS"].rating == 1400.0

    latest = client.get("/api/tournaments/cup/ratings", headers=organizer).json()
    assert latest["ratings"] == 2


def test_snapshot_drift_rejected_when_no_page_parses(client, auth_headers):
    organizer = make_organizer(client, auth_headers)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    fencer = auth_headers(email="jan@example.com", name="Jan N")
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer)
    client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )

    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = "<html>redesigned fighter page</html>"
    wire_fetcher(fetcher)

    response = client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer)
    assert response.status_code == 502
    assert "drift" in response.json()["detail"]["detail"]["reason"]
    latest = client.get("/api/tournaments/cup/ratings", headers=organizer).json()
    assert latest["taken_at"] is None  # nothing stored
