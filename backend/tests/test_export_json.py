"""Canonical JSON export: versioned schema and round-trip fidelity."""

import io
from decimal import Decimal

from app.export_json import SCHEMA_VERSION
from app.importer import get_import_parser
from tests.conftest import enable_payments, publish
from tests.test_import import CSV, FakeParser


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    for code in ("LS", "SA"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": code, "weapon": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    publish(client, organizer, "cup")


def make_statement(vs, amount="1 000,00"):
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    )
    row = f"9001;14.07.2026;{amount};CZK;{vs};;;VS {vs};Jan Novak;123/0800"
    return ("meta;data\n\n" + header + "\n" + row + "\n").encode()


def normalized_sheet(client, headers, slug):
    """Sheet with deployment-local identifiers stripped: registration row ids
    and rule ids are remapped on restore, everything else must match."""
    sheet = client.get(f"/api/tournaments/{slug}/sheet", headers=headers).json()
    rows = []
    for row in sorted(sheet["rows"], key=lambda r: (r["registered_at"] or "", r["name"] or "")):
        rows.append({k: v for k, v in row.items() if k not in ("id", "_merged_into")})
    edits = sorted(
        (e["phase"], e["field"], str(e["before"]), str(e["after"]), e["actor"])
        for e in sheet["edits"]
    )
    return rows, edits


def fresh_deployment(client, auth_headers):
    """Point the app at an empty database and return (headers, client) for it —
    the only way to restore a document beside its original, since VS is unique
    across the deployment."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db import Base, get_session
    from app.main import app

    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with Session(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    return auth_headers(), client


def test_round_trip_reconstructs_fencer_table(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)

    # in-app registration, paid through the bank-statement path
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(make_statement(vs)), "text/csv")},
        headers=organizer,
    )

    # imported table rows plus a manual edit rule
    from app.main import app

    app.dependency_overrides[get_import_parser] = lambda: FakeParser()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "field_edit", "target": "reg:1",
              "payload": {"field": "club", "value": "Poznaň HEMA"}},
        headers=organizer,
    )

    export = client.get("/api/tournaments/cup/export/json", headers=organizer)
    assert export.status_code == 200
    document = export.json()
    assert document["schema_version"] == SCHEMA_VERSION
    assert len(document["registrations"]) == 1
    assert document["registrations"][0]["state"] == "paid"
    assert len(document["import_batches"][0]["rows"]) == 2

    original = normalized_sheet(client, organizer, "cup")

    # re-import into an empty deployment: a fresh database behind the same app
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db import Base, get_session

    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with Session(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    new_organizer = auth_headers()  # same email/name, empty deployment
    restore = client.post("/api/tournaments/restore", json=document, headers=new_organizer)
    assert restore.status_code == 201, restore.text

    restored = normalized_sheet(client, new_organizer, "cup")
    assert restored == original


def test_restore_refuses_taken_slug_and_bad_version(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert client.post(
        "/api/tournaments/restore", json=document, headers=organizer
    ).status_code == 409

    document["tournament"]["slug"] = "other"
    document["schema_version"] = 99
    assert client.post(
        "/api/tournaments/restore", json=document, headers=organizer
    ).status_code == 422


def test_restore_accepts_v1_organizer_names(client, auth_headers):
    """A v1 export carried `organizer_names: list[str]` on the tournament
    document; restore normalizes it into the v2 `organizers` shape (design D5)."""
    organizer = auth_headers()
    v1_document = {
        "schema_version": 1,
        "exported_at": "2026-01-01T00:00:00+00:00",
        "tournament": {
            "slug": "legacy-2025",
            "display_name": "Legacy Duel",
            "date": "2025-05-01",
            "language": "cs",
            "reservation_validity_days": 10,
            "reminder_day": 5,
            "amount_tolerance_percent": 5,
            "refundable_until": None,
            "bank_account": None,
            "unpaid_list_treatment": "greyed",
            "early_bird_until": None,
            "weapon_rental_fee": 0,
            "weapon_rental_fee_early": None,
            "afterparty_fee": 0,
            "afterparty_fee_early": None,
            "location": "Old Hall",
            "organizer_names": ["Legacy Club"],
            "discounts": [],
            "registration_opens": None,
            "registration_closes": None,
        },
        "disciplines": [],
        "extra_items": [],
        "fencers": [],
        "registrations": [],
        "bank_transactions": [],
        "import_batches": [],
        "decisions": [],
        "rules": [],
    }
    restore = client.post("/api/tournaments/restore", json=v1_document, headers=organizer)
    assert restore.status_code == 201, restore.text

    detail = client.get("/api/tournaments/legacy-2025", headers=organizer)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["organizers"] == [{"name": "Legacy Club", "link": None}]
    assert body["description"] is None
    assert body["qualification_open"] is True
    assert body["qualification_criteria"] is None
    # v3 fields default to the pre-currency behavior
    assert body["local_currency"] == "CZK"
    assert body["eur_payments_enabled"] is False
    assert body["eur_rate"] is None
    assert body["registration_instructions"] is None


def test_restore_accepts_a_v2_document_without_currency_fields(client, auth_headers):
    """A v2 export predates the currency and option columns; it must restore as
    a CZK, EUR-off tournament whose items declare no option."""
    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "t-shirt", "category": "merch", "price": 300, "max_qty": 5},
        headers=organizer,
    )
    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()

    # strip the v3 additions and re-stamp the document as v2
    document["schema_version"] = 2
    document["tournament"]["slug"] = "cup-v2"
    for field in (
        "local_currency",
        "eur_payments_enabled",
        "eur_rate",
        "registration_instructions",
    ):
        document["tournament"].pop(field)
    for item in document["extra_items"]:
        item.pop("option_label")
        item.pop("option_choices")
    for registration in document["registrations"]:
        for extra in registration["extras"]:
            extra.pop("option_value")

    restore = client.post("/api/tournaments/restore", json=document, headers=organizer)
    assert restore.status_code == 201, restore.text

    body = client.get("/api/tournaments/cup-v2", headers=organizer).json()
    assert body["local_currency"] == "CZK"
    assert body["eur_payments_enabled"] is False
    assert body["eur_rate"] is None
    assert body["registration_instructions"] is None
    assert body["extra_items"][0]["option_label"] is None
    assert body["extra_items"][0]["option_choices"] == []


def test_v3_currency_and_option_fields_round_trip(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    # the tournament is already published: give every discipline its EUR
    # price before enabling EUR mode (design D3 of add-explicit-publishing)
    for code in ("LS", "SA"):
        client.patch(
            f"/api/tournaments/cup/disciplines/{code}",
            json={"slug": code, "weapon": code, "capacity": 10, "fee": 1000, "fee_eur": 40},
            headers=organizer,
        )
    client.patch(
        "/api/tournaments/cup",
        json={
            "eur_payments_enabled": True,
            "eur_rate": "25.5",
            "registration_instructions": "Plať do 10 dnů.",
        },
        headers=organizer,
    )
    item = client.post(
        "/api/tournaments/cup/extra-items",
        json={
            "name": "t-shirt",
            "category": "merch",
            "price": 300,
            "price_eur": 12,
            "max_qty": 5,
            "option_label": "size",
            "option_choices": ["S", "M"],
        },
        headers=organizer,
    ).json()
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": ["LS"],
            "extras": [{"extra_item_id": item["id"], "qty": 2, "option_value": "M"}],
        },
        headers=fencer,
    )

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert document["schema_version"] == SCHEMA_VERSION
    assert document["tournament"]["local_currency"] == "CZK"
    assert document["tournament"]["eur_payments_enabled"] is True
    assert document["tournament"]["eur_rate"] == "25.50"
    assert document["extra_items"][0]["option_choices"] == ["S", "M"]
    assert document["extra_items"][0]["price_eur"] == 12
    assert document["registrations"][0]["extras"][0]["option_value"] == "M"
    assert document["registrations"][0]["total_amount"] == 1600  # 1000 + 2×300
    assert document["registrations"][0]["total_eur"] == 64  # 40 + 2×12

    # restore into an empty deployment: VS is globally unique, so a copy cannot
    # land beside its original
    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post(
        "/api/tournaments/restore", json=document, headers=new_organizer
    )
    assert restore.status_code == 201, restore.text

    body = restore_client.get("/api/tournaments/cup", headers=new_organizer).json()
    assert body["eur_payments_enabled"] is True
    assert Decimal(body["eur_rate"]) == Decimal("25.5")
    assert body["registration_instructions"] == "Plať do 10 dnů."
    assert body["extra_items"][0]["option_label"] == "size"
    assert body["extra_items"][0]["option_choices"] == ["S", "M"]
    assert body["extra_items"][0]["price_eur"] == 12
    assert body["disciplines"][0]["fee_eur"] == 40

    # re-exporting the restored deployment proves the selection's option value
    # survived the round trip, not just the item's definition
    # the document carries no publication record, so what restore lands is a
    # draft — one holding registrations, which it keeps and may be read, and
    # which must be published before it exports again (spec data-export)
    publish(restore_client, new_organizer, "cup")
    again = restore_client.get(
        "/api/tournaments/cup/export/json", headers=new_organizer
    ).json()
    assert again["registrations"][0]["extras"][0]["option_value"] == "M"


# ---------------------------------------------------------------------------
# 9.7 Discipline identity round-trips (design discipline-identity)
# ---------------------------------------------------------------------------


def test_tiers_round_trip(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "tiers", "display_name": "Tiers", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/tiers",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/tiers/disciplines",
        json={"slug": "LS-A", "weapon": "LS", "name": "Longsword Top", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/tiers/disciplines",
        json={"slug": "LS-B", "weapon": "LS", "name": "Longsword Open", "capacity": 12, "fee": 500},
        headers=organizer,
    )
    publish(client, organizer, "tiers")
    top = auth_headers(email="top@example.com", name="Top")
    client.post("/api/tournaments/tiers/register", json={"disciplines": ["LS-A"]}, headers=top)
    openf = auth_headers(email="open@example.com", name="Open")
    client.post("/api/tournaments/tiers/register", json={"disciplines": ["LS-B"]}, headers=openf)

    document = client.get("/api/tournaments/tiers/export/json", headers=organizer).json()
    by_slug = {d["slug"]: d for d in document["disciplines"]}
    assert by_slug.keys() == {"LS-A", "LS-B"}
    assert by_slug["LS-A"]["capacity"] == 10
    assert by_slug["LS-B"]["capacity"] == 12

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post(
        "/api/tournaments/restore", json=document, headers=new_organizer
    )
    assert restore.status_code == 201, restore.text
    detail = restore_client.get("/api/tournaments/tiers", headers=new_organizer).json()
    slugs = {d["slug"]: d for d in detail["disciplines"]}
    assert slugs.keys() == {"LS-A", "LS-B"}
    assert slugs["LS-A"]["name"] == "Longsword Top"
    publish(restore_client, new_organizer, "tiers")
    export2 = restore_client.get(
        "/api/tournaments/tiers/export/json", headers=new_organizer
    ).json()
    entries_by_email = {r["fencer_email"]: r["entries"] for r in export2["registrations"]}
    assert entries_by_email["top@example.com"][0]["slug"] == "LS-A"
    assert entries_by_email["open@example.com"][0]["slug"] == "LS-B"


def test_individual_and_team_in_one_weapon_round_trip(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "mixed", "display_name": "Mixed", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/mixed",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/mixed/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/mixed/disciplines",
        json={
            "slug": "LS-Team", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    publish(client, organizer, "mixed")
    solo = auth_headers(email="solo@example.com", name="Solo")
    client.post("/api/tournaments/mixed/register", json={"disciplines": ["LS"]}, headers=solo)
    captain = auth_headers(email="captain@example.com", name="Captain")
    client.post(
        "/api/tournaments/mixed/register",
        json={"disciplines": [], "teams": [{"slug": "LS-Team", "name": "Wolves"}]},
        headers=captain,
    )

    document = client.get("/api/tournaments/mixed/export/json", headers=organizer).json()
    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post(
        "/api/tournaments/restore", json=document, headers=new_organizer
    )
    assert restore.status_code == 201, restore.text
    publish(restore_client, new_organizer, "mixed")
    export2 = restore_client.get(
        "/api/tournaments/mixed/export/json", headers=new_organizer
    ).json()
    by_email = {r["fencer_email"]: r for r in export2["registrations"]}
    assert by_email["solo@example.com"]["entries"][0]["slug"] == "LS"
    assert by_email["captain@example.com"]["teams"][0]["discipline_slug"] == "LS-Team"
    assert by_email["captain@example.com"]["entries"] == []


def test_dangling_discipline_slug_rejected(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document["tournament"]["slug"] = "dangling"
    document["tournament"]["vs_series"] = 77  # avoid colliding with "cup" in the same DB
    document["fencers"] = [
        {"email": "ghost@example.com", "display_name": "Ghost", "hr_id": None,
         "nationality": None, "club": None}
    ]
    document["registrations"] = [
        {
            "ref": 1,
            "fencer_email": "ghost@example.com",
            "registered_at": "2026-01-01T00:00:00+00:00",
            "state": "reserved",
            "vs": None,
            "total_amount": 0,
            "total_eur": None,
            "expires_at": None,
            "reminded_at": None,
            "paid_at": None,
            "cancelled_at": None,
            "refundable": None,
            "refund_state": "not_applicable",
            "weapon_rentals": [],
            "afterparty": False,
            "aftersparring": False,
            "accommodation": None,
            "notes": None,
            "entries": [{"slug": "NO-SUCH-SLUG", "is_substitute": False}],
            "extras": [],
            "teams": [],
        }
    ]
    response = client.post("/api/tournaments/restore", json=document, headers=organizer)
    assert response.status_code == 422
    assert "NO-SUCH-SLUG" in response.text
    # no partial registration created
    assert client.get(
        "/api/tournaments/dangling", headers=organizer
    ).status_code == 404


def test_pre_version_document_restores_with_code_as_slug(client, auth_headers):
    """A document produced before disciplines carried a classification (no
    `slug`/`weapon`/`gender`/`material`, only `code`) restores with the old
    code taken as the slug and the classification parsed from it (design
    discipline-identity Migration Plan)."""
    organizer = auth_headers()
    document = {
        "schema_version": 6,
        "exported_at": "2026-01-01T00:00:00+00:00",
        "tournament": {
            "slug": "legacy-classification",
            "display_name": "Legacy",
            "date": "2026-11-01",
            "language": "cs",
            "reservation_validity_days": 10,
            "reminder_day": 5,
            "amount_tolerance_percent": 5,
            "refundable_until": None,
            "bank_account": None,
            "unpaid_list_treatment": "greyed",
            "early_bird_until": None,
            "weapon_rental_fee": 0,
            "weapon_rental_fee_early": None,
            "afterparty_fee": 0,
            "afterparty_fee_early": None,
            "location": "Prague",
            "description": None,
            "qualification_open": True,
            "qualification_criteria": None,
            "registration_instructions": None,
            "local_currency": "CZK",
            "eur_payments_enabled": False,
            "eur_rate": None,
            "organizers": [{"name": "Legacy Org", "link": None}],
            "discounts": [],
            "registration_opens": None,
            "registration_closes": None,
            "vs_year": 2026,
            "vs_series": 51,
            "vs_next_seq": 1,
            "team_composition_deadline": None,
        },
        "disciplines": [
            {"code": "Plastic SAW", "name": "Sabre Women (Plastic)", "capacity": 10,
             "fee": 500, "fee_early": None, "fee_eur": None, "fee_early_eur": None},
        ],
        "extra_items": [],
        "fencers": [],
        "registrations": [],
        "bank_transactions": [],
        "import_batches": [],
        "decisions": [],
        "rules": [],
    }
    restore = client.post("/api/tournaments/restore", json=document, headers=organizer)
    assert restore.status_code == 201, restore.text
    detail = client.get("/api/tournaments/legacy-classification", headers=organizer).json()
    discipline = detail["disciplines"][0]
    assert discipline["slug"] == "Plastic SAW"
    assert discipline["weapon"] == "SA"
    assert discipline["gender"] == "W"
    assert discipline["material"] == "Plastic"


def test_opening_moment_round_trips(client, auth_headers):
    """The opening time and the zone survive an export and its reimport, so a
    tournament restored from a file opens at the same instant it did before
    (change add-registration-open-time)."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "evening", "display_name": "Evening", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/evening",
        json={
            "location": "Brno",
            "organizers": [{"name": "Org", "link": None}],
            "registration_opens": "2026-09-01",
            "registration_opens_time": "18:00:00",
            "timezone": "Europe/Prague",
        },
        headers=organizer,
    )
    # a discipline and a publish only so the tournament can be exported at all
    # (spec data-export, Exporting waits for publication)
    client.post(
        "/api/tournaments/evening/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "evening")
    before = client.get("/api/tournaments/evening", headers=organizer).json()
    assert before["registration_opens_at"] == "2026-09-01T16:00:00Z"

    document = client.get("/api/tournaments/evening/export/json", headers=organizer).json()
    assert document["tournament"]["registration_opens_time"] == "18:00:00"
    assert document["tournament"]["timezone"] == "Europe/Prague"

    fresh_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post(
        "/api/tournaments/restore", json=document, headers=fresh_organizer
    )
    assert restore.status_code == 201, restore.text
    after = restore_client.get("/api/tournaments/evening", headers=fresh_organizer).json()
    assert after["registration_opens_time"] == "18:00:00"
    assert after["timezone"] == "Europe/Prague"
    assert after["registration_opens_at"] == before["registration_opens_at"]


def test_document_without_an_opening_time_restores_with_the_default_zone(client, auth_headers):
    """A file written before the opening moment existed carries neither field;
    it lands with no time and the default zone, exactly as the migration
    backfilled the tournaments it was taken from."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "older", "display_name": "Older", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/older",
        json={
            "location": "Brno",
            "organizers": [{"name": "Org", "link": None}],
            "registration_opens": "2026-09-01",
        },
        headers=organizer,
    )
    client.post(
        "/api/tournaments/older/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "older")
    document = client.get("/api/tournaments/older/export/json", headers=organizer).json()
    document["schema_version"] = 7
    del document["tournament"]["registration_opens_time"]
    del document["tournament"]["timezone"]

    fresh_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post(
        "/api/tournaments/restore", json=document, headers=fresh_organizer
    )
    assert restore.status_code == 201, restore.text
    after = restore_client.get("/api/tournaments/older", headers=fresh_organizer).json()
    assert after["registration_opens_time"] is None
    assert after["timezone"] == "Europe/Prague"


def test_manual_rows_round_trip_with_their_numbers(client, auth_headers):
    """Hand-entered fencers survive export and restore whole, keeping the
    numbers they were given (3.5)."""
    organizer = auth_headers()
    setup(client, organizer)
    entered = client.post(
        "/api/tournaments/cup/manual-rows",
        json={
            "name": "Hand Entered",
            "club": "Twerchhau",
            "nationality": "CZ",
            "hr_id": 4321,
            "disciplines": ["LS"],
            "registered_at": "2026-05-01T10:00:00",
            "notes": "paid at the door",
        },
        headers=organizer,
    )
    assert entered.status_code == 201, entered.text
    row = next(
        r
        for r in client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
        if r["id"].startswith("man:")
    )
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": "field_edit",
            "target": row["id"],
            "payload": {"field": "club", "value": "Mordschlag"},
        },
        headers=organizer,
    )

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert len(document["manual_rows"]) == 1
    original = normalized_sheet(client, organizer, "cup")

    new_organizer, _ = fresh_deployment(client, auth_headers)
    restore = client.post("/api/tournaments/restore", json=document, headers=new_organizer)
    assert restore.status_code == 201, restore.text

    assert normalized_sheet(client, new_organizer, "cup") == original
    restored = next(
        r
        for r in client.get("/api/tournaments/cup/sheet", headers=new_organizer).json()["rows"]
        if r["id"].startswith("man:")
    )
    assert restored["number"] == row["number"]
    assert restored["club"] == "Mordschlag"


def test_document_without_manual_rows_restores(client, auth_headers):
    """A document written before hand entry existed carries no such key (3.5)."""
    organizer = auth_headers()
    setup(client, organizer)
    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document.pop("manual_rows")
    document["schema_version"] = 9

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert (
        client.post("/api/tournaments/restore", json=document, headers=new_organizer).status_code
        == 201
    )


def test_arrival_order_numbers_a_numberless_document(client, auth_headers):
    """A document recording no numbers is numbered in the order rows entered:
    registrations, then the imported batch, then the hand-entered rows (3.4)."""
    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments/cup/manual-rows",
        json={
            "name": "Hand Entered",
            "disciplines": ["LS"],
            "registered_at": "2020-01-01T10:00:00",
        },
        headers=organizer,
    )
    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document.pop("row_numbers")

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert (
        client.post("/api/tournaments/restore", json=document, headers=new_organizer).status_code
        == 201
    )

    rows = client.get("/api/tournaments/cup/sheet", headers=new_organizer).json()["rows"]
    numbered = {row["id"].split(":")[0]: row["number"] for row in rows}
    # the manual row states the earliest moment, so it is displayed first while
    # carrying the highest number — arrival, not display, is what numbers
    assert numbered["man"] == max(numbered.values())
    assert [row["id"].split(":")[0] for row in rows][0] == "man"


def test_two_addressless_fencers_survive_a_round_trip(client, auth_headers):
    """Keyed by address, an export collapsed every record without one onto a
    single `None` — writing out one fencer where the tournament held two, and
    pointing both registrations at whichever survived. Schema 12 keys on `ref`.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db import Base, get_session
    from app.main import app
    from app.models import Fencer, Registration
    from tests.test_issuing import import_roster, issue, row
    from tests.test_issuing import setup as issue_setup

    organizer = auth_headers()
    issue_setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Milan Diviš", "divis@example.com"),
            row("Václav Pekárek", "divis@example.com"),
            row("Jindřich Pekárek", "divis@example.com"),
        ],
    )
    assert issue(client, organizer)["issued"] == 3

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()

    refs = [f["ref"] for f in document["fencers"]]
    assert len(refs) == len(set(refs)) == 3
    assert sum(1 for f in document["fencers"] if f["email"] is None) == 2
    assert {r["fencer_ref"] for r in document["registrations"]} == set(refs)

    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with Session(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    new_organizer = auth_headers()
    restore = client.post("/api/tournaments/restore", json=document, headers=new_organizer)
    assert restore.status_code == 201, restore.text

    with Session(fresh) as check:
        names = sorted(
            f.display_name
            for f in check.scalars(select(Fencer).where(Fencer.email.is_(None))).all()
        )
        assert names == ["Jindřich Pekárek", "Václav Pekárek"]
        assert len(check.scalars(select(Registration)).all()) == 3


# ------------------------------- hand-recorded payments and waivers (v13)


def _restore_into_empty(client, auth_headers, document):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db import Base, get_session
    from app.main import app

    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with Session(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    organizer = auth_headers()
    restore = client.post("/api/tournaments/restore", json=document, headers=organizer)
    assert restore.status_code == 201, restore.text
    return organizer


def _restored_manual_payments():
    """What the restored deployment holds, read directly. `restored` above is
    the same app pointed at a fresh database, so its session override is the
    way in."""
    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import ManualPayment

    session = next(app.dependency_overrides[get_session]())
    return list(session.scalars(select(ManualPayment)).all())


def _registration_id(client, organizer, vs):
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    return next(row["registration_id"] for row in rows if row["vs"] == vs)


def test_a_recorded_cash_payment_round_trips(client, auth_headers):
    """The credited counter may now hold money no transaction explains, so the
    document must carry the payment that does (spec data-export)."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]
    client.post(
        "/api/tournaments/cup/payments/manual",
        json={
            "registration_id": _registration_id(client, organizer, vs),
            "amount": "1000.00",
            "currency": "CZK",
            "received_on": "2026-08-01",
            "method": "cash",
            "note": "u prezence",
        },
        headers=organizer,
    )

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    [payment] = document["manual_payments"]
    assert payment["amount_cents"] == 100000
    assert payment["method"] == "cash"
    assert payment["note"] == "u prezence"
    assert document["registrations"][0]["amount_paid_cents"] == 100000

    restored = _restore_into_empty(client, auth_headers, document)
    rows = client.get("/api/tournaments/cup/sheet", headers=restored).json()["rows"]
    [row] = [r for r in rows if r["vs"] == vs]
    assert row["paid"] is True
    # the credit is restored once, from the counters, and not replayed on top
    # of them by the payment record beside them
    assert row["outstanding_amount"] == "0.00"
    # read from the database rather than the console: a restored tournament
    # carries no feature flags at all, which is older than this change and
    # outside it
    assert [p.amount_cents for p in _restored_manual_payments()] == [100000]


def test_a_waiver_round_trips(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]
    registration_id = _registration_id(client, organizer, vs)
    assert client.post(
        f"/api/tournaments/cup/registrations/{registration_id}"
        "/settled?settled=True&reason=volná účast",
        headers=organizer,
    ).status_code == 200

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    [entry] = document["registrations"]
    assert entry["settled_by_hand_reason"] == "volná účast"
    assert entry["settled_by_hand_at"] is not None
    assert entry["amount_paid_cents"] == 0

    restored = _restore_into_empty(client, auth_headers, document)
    rows = client.get("/api/tournaments/cup/sheet", headers=restored).json()["rows"]
    [row] = [r for r in rows if r["vs"] == vs]
    assert row["paid"] is True
    assert row["settled_by_hand"] is True
    assert row["settled_by_hand_reason"] == "volná účast"


def test_a_removed_payment_is_not_exported(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]
    payment = client.post(
        "/api/tournaments/cup/payments/manual",
        json={
            "registration_id": _registration_id(client, organizer, vs),
            "amount": "1000.00",
            "currency": "CZK",
            "received_on": "2026-08-01",
            "method": "cash",
        },
        headers=organizer,
    ).json()
    client.delete(
        f"/api/tournaments/cup/payments/manual/{payment['id']}", headers=organizer
    )

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert document["manual_payments"] == []


def test_a_pre_v13_document_restores_unmarked(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document["schema_version"] = 12
    document.pop("manual_payments")
    for entry in document["registrations"]:
        entry.pop("settled_by_hand_at")
        entry.pop("settled_by_hand_reason")

    restored = _restore_into_empty(client, auth_headers, document)
    rows = client.get("/api/tournaments/cup/sheet", headers=restored).json()["rows"]
    [row] = [r for r in rows if r["vs"] == vs]
    assert row["settled_by_hand"] is False
    assert _restored_manual_payments() == []
