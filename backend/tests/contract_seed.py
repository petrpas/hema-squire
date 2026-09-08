"""The state `tests/test_api_contract.py` fuzzes against.

Without it the contract suite proves very little. Schemathesis generates path
parameters from the schema, so `{slug}` arrives as a random string and every
operation under a tournament answers 404 before its handler runs. Measured on
the unseeded suite: 8222 requests, 75.6% of them 404, and 15 of 108 operations
ever reached a 2xx. The other 93 were testing the 404 path.

So this builds one tournament with something of everything the routes address,
and the suite substitutes the real ids for the generated ones. What is then
fuzzed is the request *bodies and queries* — where the bugs are — rather than
the id space, where a random value only ever proves that 404 works.

Not a fixture for general use: it is deliberately maximal and slow-ish, and a
test that wants a tournament of its own should keep building the one it needs.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import sheets_export
from app.main import app
from app.models import Fencer, Registration, Role
from tests.conftest import publish, set_features, set_fio_token
from tests.test_bank import FIO_CSV

SLUG = "cup"
DISCIPLINE = "LS"
TEAM_DISCIPLINE = "TeamLS"


class StubSheet:
    """A spreadsheet that remembers what was written to it.

    Without one, `POST /export/sheet` answers 503 `sheets_not_configured` and
    the export is never exercised — the same wall the Fio stub in `conftest`
    exists to get past, for the same reason.
    """

    def __init__(self) -> None:
        self.grids: dict[str, list[list[str]]] = {}

    def read(self, worksheet: str) -> list[list[str]] | None:
        return self.grids.get(worksheet)

    def write(self, worksheet: str, grid: list[list[str]]) -> None:
        self.grids[worksheet] = grid


@dataclass
class Seed:
    """Real values for every path parameter the schema names."""

    headers: dict[str, str]
    path_params: dict[str, object] = field(default_factory=dict)


def build(client, auth_headers, engine) -> Seed:
    organizer = auth_headers()
    # Admin, not merely organizer: `/api/admin/*` is a fifth of the surface and
    # answers 403 to anything less, which is another wall the fuzzer would
    # spend its examples on. Fuzzing as the most privileged caller is what
    # reaches the most handler code.
    with Session(engine) as session:
        account = session.scalar(select(Fencer).where(Fencer.email == "organizer@example.com"))
        account.role = Role.ADMIN
        session.commit()

    client.post(
        "/api/tournaments",
        json={"slug": SLUG, "display_name": "Cup", "date": "2026-12-01"},
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{SLUG}/disciplines",
        json={"slug": DISCIPLINE, "weapon": "LS", "capacity": 8, "fee": 800},
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{SLUG}/disciplines",
        json={
            "slug": TEAM_DISCIPLINE, "weapon": "LS", "capacity": 4, "fee": 3000,
            "kind": "team", "team_min": 2, "team_max": 4,
        },
        headers=organizer,
    )
    item = client.post(
        f"/api/tournaments/{SLUG}/extra-items",
        json={"name": "Banquet", "category": "afterparty", "price": 300},
        headers=organizer,
    ).json()
    # every flag on: a feature that is off takes its endpoints out of reach
    set_features(
        client, organizer, SLUG,
        feature_payments=True, feature_extras=True, feature_teams=True, feature_schedule=True,
    )
    publish(client, organizer, SLUG)
    set_fio_token(client, organizer, SLUG)
    client.patch(
        f"/api/tournaments/{SLUG}",
        json={"output_sheet_url": "https://docs.google.com/spreadsheets/d/seed"},
        headers=organizer,
    )
    app.dependency_overrides[sheets_export.get_sheets_client_factory] = (
        lambda: lambda tournament: StubSheet()
    )

    fencer = auth_headers(email="f1@example.com", name="F1", role=Role.FENCER)
    registration = client.post(
        f"/api/tournaments/{SLUG}/register",
        json={
            "disciplines": [DISCIPLINE],
            "teams": [{"slug": TEAM_DISCIPLINE, "name": "Wolves"}],
        },
        headers=fencer,
    ).json()
    # the registration id is not in its own response — the fencer-facing body
    # states the symbol, not the row — so it is read back from the database
    with Session(engine) as session:
        row = session.scalar(select(Registration))
        registration_id, fencer_id = row.id, row.fencer_id

    client.post("/api/account/plea", json={"message": "please"}, headers=fencer)
    pleas = client.get("/api/admin/pleas", headers=organizer).json()

    payment = client.post(
        f"/api/tournaments/{SLUG}/payments/manual",
        json={
            "registration_id": registration_id, "amount": 800, "currency": "CZK",
            "received_on": "2026-11-01", "method": "cash",
        },
        headers=organizer,
    ).json()
    rule = client.post(
        f"/api/tournaments/{SLUG}/rules",
        json={
            "phase": "manual", "kind": "field_edit", "target": "1",
            "payload": {"field": "club", "value": "X"},
        },
        headers=organizer,
    ).json()
    client.post(
        f"/api/tournaments/{SLUG}/payments/import-statement",
        files={"file": ("v.csv", FIO_CSV, "text/csv")},
        headers=organizer,
    )
    transactions = client.get(
        f"/api/tournaments/{SLUG}/payments/transactions", headers=organizer
    ).json()

    return Seed(
        headers=organizer,
        path_params={
            "slug": SLUG,
            "discipline_slug": DISCIPLINE,
            "item_id": item["id"],
            "team_id": registration["teams"][0]["id"],
            "registration_id": registration_id,
            "fencer_id": fencer_id,
            "plea_id": pleas[0]["id"],
            "payment_id": payment["id"],
            "rule_id": rule["id"],
            "transaction_id": transactions[0]["id"],
        },
    )
