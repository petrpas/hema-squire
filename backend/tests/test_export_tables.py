"""The Export phase's tables: ratings in the projection and the organizer's
correction of one (spec export-tables, The rating is the organizer's to
correct)."""

from app.hr_sync import get_hr_fetcher
from app.main import app
from tests.conftest import publish
from tests.test_sheets_export import FakeHRFetcher, fighter_page

LONGSWORD = "Mixed & Men's Steel Longsword"
SABRE = "Mixed & Men's Steel Sabre"


def organizer_with_tournament(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    for code in ("LS", "SA"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": code, "weapon": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    publish(client, organizer, "cup")
    return organizer


def register_bound_fencer(client, auth_headers, disciplines=("LS", "SA")):
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer)
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines)},
        headers=fencer,
    )
    return fencer


def take_snapshot(client, organizer, categories):
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page(categories)
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher
    response = client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer)
    assert response.status_code == 200, response.text


def sheet_rows(client, organizer):
    body = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return {row["name"]: row for row in body["rows"]}, body["edits"]


def override(client, organizer, target, slug, rating):
    response = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "export",
            "kind": "rating_override",
            "target": target,
            "payload": {"discipline": slug, "rating": rating},
        },
        headers=organizer,
    )
    return response


def test_fetched_ratings_reach_the_projection(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20), (SABRE, 1100.0, 44)])

    rows, _ = sheet_rows(client, organizer)
    jan = rows["Jan Novák"]
    assert jan["ratings"] == {"LS": 1400.0, "SA": 1100.0}
    assert jan["ranks"] == {"LS": 20, "SA": 44}


def test_typed_rating_survives_replay_and_names_its_discipline(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20), (SABRE, 1100.0, 44)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]

    assert override(client, organizer, target, "LS", 1555.0).status_code == 201

    rows, edits = sheet_rows(client, organizer)
    jan = rows["Jan Novák"]
    assert jan["ratings"]["LS"] == 1555.0
    # the other discipline still states what HEMA Ratings says, and so does the
    # rank beside the correction
    assert jan["ratings"]["SA"] == 1100.0
    assert jan["ranks"]["LS"] == 20
    edit = next(e for e in edits if e["field"] == "rating:LS")
    assert (edit["before"], edit["after"]) == (1400.0, 1555.0)


def test_removing_the_override_exposes_the_fetched_rating(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]
    rule_id = override(client, organizer, target, "LS", 1555.0).json()["id"]

    client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)

    rows, edits = sheet_rows(client, organizer)
    assert rows["Jan Novák"]["ratings"]["LS"] == 1400.0
    assert not [e for e in edits if e["field"] == "rating:LS"]


def test_a_new_snapshot_does_not_displace_an_override(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20), (SABRE, 1100.0, 44)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]
    override(client, organizer, target, "LS", 1555.0)

    take_snapshot(client, organizer, [(LONGSWORD, 1480.0, 12), (SABRE, 1190.0, 30)])

    rows, _ = sheet_rows(client, organizer)
    jan = rows["Jan Novák"]
    assert jan["ratings"]["LS"] == 1555.0  # the correction stands
    assert jan["ratings"]["SA"] == 1190.0  # everyone else is freshly fetched
    assert jan["ranks"]["LS"] == 12  # the register's own figure moves


def test_override_refuses_a_discipline_the_tournament_does_not_offer(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]

    response = override(client, organizer, target, "RAPIER", 1555.0)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unknown_discipline_slug"


def test_override_refuses_a_rating_that_is_not_a_number(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]

    response = override(client, organizer, target, "LS", "vysoké")
    assert response.status_code == 422


def test_a_rating_can_be_corrected_to_none(client, auth_headers):
    """Null is a rating an organizer states — the register has nobody by that
    name — and is not the same as removing the rule."""
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers)
    take_snapshot(client, organizer, [(LONGSWORD, 1400.0, 20)])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]

    assert override(client, organizer, target, "LS", None).status_code == 201

    rows, _ = sheet_rows(client, organizer)
    assert rows["Jan Novák"]["ratings"]["LS"] is None


def add_item(client, organizer, name, category, **fields):
    payload = {"name": name, "category": category, "price": 300, "max_qty": 5, **fields}
    response = client.post("/api/tournaments/cup/extra-items", json=payload, headers=organizer)
    assert response.status_code == 201, response.text
    return response.json()


def test_extras_project_per_category_with_quantities(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    shirt = add_item(client, organizer, "t-shirt", "merch", option_label="size")
    mug = add_item(client, organizer, "mug", "merch")
    sword = add_item(client, organizer, "feder", "rental")
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": ["LS"],
            "extras": [
                {"extra_item_id": shirt["id"], "qty": 2, "option_value": "M"},
                {"extra_item_id": mug["id"]},
                {"extra_item_id": sword["id"]},
            ],
        },
        headers=fencer,
    )

    rows, _ = sheet_rows(client, organizer)
    extras = rows["Jan Novák"]["extras"]
    assert extras["merch"] == [
        {"name": "t-shirt", "qty": 2, "option": "M"},
        {"name": "mug", "qty": 1, "option": None},
    ]
    assert extras["rental"] == [{"name": "feder", "qty": 1, "option": None}]
    # a category the fencer bought nothing in is absent, so a tab's population
    # is the rows holding its key
    assert "seminar" not in extras


def tabs(client, organizer):
    response = client.get("/api/tournaments/cup/export/tables", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def table(client, organizer, kind, key=""):
    response = client.get(
        "/api/tournaments/cup/export/table",
        params={"kind": kind, "key": key},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_the_band_is_derived_from_the_tournament(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    add_item(client, organizer, "t-shirt", "merch")
    add_item(client, organizer, "feder", "rental")

    band = [(tab["kind"], tab["key"]) for tab in tabs(client, organizer)]
    assert band == [
        ("fencers", ""),
        ("discipline", "LS"),
        ("discipline", "SA"),
        ("category", "rental"),  # goods before programme
        ("category", "merch"),
    ]


def test_a_team_discipline_has_no_tab(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 3,
            "team_max": 3,
            "capacity": 8,
            "fee": 3000,
        },
        headers=organizer,
    )

    keys = [tab["key"] for tab in tabs(client, organizer) if tab["kind"] == "discipline"]
    assert keys == ["LS", "SA"]


def test_a_discipline_tab_states_its_capacity_and_its_line(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    longsword = next(t for t in tabs(client, organizer) if t["key"] == "LS")
    assert (longsword["capacity"], longsword["line"]) == (10, "queue")


def test_a_deleted_row_is_in_no_table(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers, disciplines=["LS"])
    rows, _ = sheet_rows(client, organizer)
    target = rows["Jan Novák"]["id"]
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "export", "kind": "row_delete", "target": target, "payload": {}},
        headers=organizer,
    )

    assert table(client, organizer, "fencers")["rows"] == []
    assert table(client, organizer, "discipline", "LS")["rows"] == []


def test_an_item_table_lists_only_its_buyers(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    shirt = add_item(client, organizer, "t-shirt", "merch")
    buyer = auth_headers(email="buyer@example.com", name="Buyer One")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "extras": [{"extra_item_id": shirt["id"], "qty": 2}]},
        headers=buyer,
    )
    abstainer = auth_headers(email="none@example.com", name="Nobody Two")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=abstainer)

    merch = table(client, organizer, "category", "merch")
    assert [row["name"] for row in merch["rows"]] == ["Buyer One"]
    assert merch["rows"][0]["extras"]["merch"][0]["qty"] == 2
    assert len(table(client, organizer, "fencers")["rows"]) == 2


def test_a_table_nobody_offers_is_not_addressable(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    response = client.get(
        "/api/tournaments/cup/export/table",
        params={"kind": "category", "key": "merch"},
        headers=organizer,
    )
    assert response.status_code == 404


def test_a_discipline_table_lists_seated_and_queued_alike(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    register_bound_fencer(client, auth_headers, disciplines=["LS"])

    rows = table(client, organizer, "discipline", "LS")["rows"]
    jan = next(row for row in rows if row["name"] == "Jan Novák")
    # membership travels on the row, so the console draws the line from what it
    # already holds
    assert jan["disciplines"] == ["LS"]
    assert jan["substitute_for"] == []


class CountingFetcher(FakeHRFetcher):
    """Counts what a refresh run actually asks HEMA Ratings for."""

    def __init__(self):
        super().__init__()
        self.fetches: list[int] = []

    def fighter_page(self, hr_id: int) -> str | None:
        self.fetches.append(hr_id)
        return self.pages.get(hr_id)


def test_a_refresh_fetches_each_fighter_page_once(client, auth_headers):
    """Three disciplines, one page: a fighter page carries every category at
    once, so narrowing a refresh to one discipline would save no request (spec
    hr-integration, Ratings snapshots)."""
    organizer = organizer_with_tournament(client, auth_headers)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "RA", "weapon": "RA", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    register_bound_fencer(client, auth_headers, disciplines=["LS", "SA", "RA"])

    fetcher = CountingFetcher()
    fetcher.pages[10234] = fighter_page(
        [
            (LONGSWORD, 1400.0, 20),
            (SABRE, 1100.0, 44),
            ("Mixed & Men's Steel Single Rapier", 1000.0, 60),
        ]
    )
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher
    outcome = client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer).json()

    assert fetcher.fetches == [10234]  # once, whatever the tournament's disciplines
    assert outcome["ratings"] == 3  # and the one parse answers all three

    rows, _ = sheet_rows(client, organizer)
    assert rows["Jan Novák"]["ratings"] == {"LS": 1400.0, "SA": 1100.0, "RA": 1000.0}
