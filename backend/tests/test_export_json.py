"""Canonical JSON export: versioned schema and round-trip fidelity."""

import io
from decimal import Decimal

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
    client.patch(
        "/api/tournaments/cup",
        json={
            "eur_payments_enabled": True,
            "eur_rate": "25.5",
            "registration_instructions": "Plať do 10 dnů.",
        },
        headers=organizer,
    )
    for code in ("LS", "SA"):
        client.patch(
            f"/api/tournaments/cup/disciplines/{code}",
            json={"code": code, "capacity": 10, "fee": 1000, "fee_eur": 40},
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
    again = restore_client.get(
        "/api/tournaments/cup/export/json", headers=new_organizer
    ).json()
    assert again["registrations"][0]["extras"][0]["option_value"] == "M"
