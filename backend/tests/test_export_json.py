"""Canonical JSON export: versioned schema and round-trip fidelity."""

import io

from app.export_json import SCHEMA_VERSION
from app.importer import get_import_parser
from tests.test_import import CSV, FakeParser


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    for code in ("LS", "SA"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"code": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )


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
