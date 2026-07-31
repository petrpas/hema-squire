import datetime
import io

import pytest

from app.bank import (
    IncomingTransaction,
    get_fio_client,
    parse_fio_csv,
    parse_fio_json,
)
from app.main import app

FIO_JSON = {
    "accountStatement": {
        "transactionList": {
            "transaction": [
                {
                    "column22": {"value": 26662142344},
                    "column0": {"value": "2026-07-14+0200"},
                    "column1": {"value": 1300.0},
                    "column14": {"value": "CZK"},
                    "column5": {"value": "1000001"},
                    "column16": {"value": "VS1000001 Na Duel! 2026"},
                    "column10": {"value": "Novák Jan"},
                    "column2": {"value": "123456789"},
                },
                {
                    "column22": {"value": 26662142345},
                    "column0": {"value": "2026-07-15+0200"},
                    "column1": {"value": 51.23},
                    "column14": {"value": "EUR"},
                    "column5": None,
                    "column16": {"value": "startovne"},
                    "column10": {"value": "MUELLER LUKAS"},
                    "column2": None,
                },
            ]
        }
    }
}

FIO_CSV = """\
accountId;2000145399
bankId;2010
currency;CZK

ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet
26662142344;14.07.2026;1 300,00;CZK;1000001;;;VS1000001 Na Duel!;Novák Jan;123456789
26662142346;15.07.2026;-250,00;CZK;;;;vratka;;
""".encode()


def test_parse_fio_json():
    transactions = parse_fio_json(FIO_JSON)
    assert len(transactions) == 2
    first, second = transactions
    assert first.external_id == "26662142344"
    assert first.date == datetime.date(2026, 7, 14)
    assert first.amount_cents == 130000
    assert first.vs == 1000001
    assert second.vs is None
    assert second.amount_cents == 5123
    assert second.currency == "EUR"


def test_parse_fio_csv_with_metadata_and_czech_formats():
    transactions = parse_fio_csv(FIO_CSV)
    assert len(transactions) == 2
    assert transactions[0].external_id == "26662142344"
    assert transactions[0].amount_cents == 130000
    assert transactions[0].vs == 1000001
    assert transactions[1].amount_cents == -25000
    assert transactions[1].vs is None


def test_parse_fio_csv_rejects_garbage():
    with pytest.raises(ValueError):
        parse_fio_csv(b"some;random;csv\n1;2;3\n")


def setup_tournament(client, organizer, fio_token=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    if fio_token:
        client.patch(
            "/api/tournaments/cup", json={"fio_token": fio_token}, headers=organizer
        )


def import_statement(client, headers, content=FIO_CSV):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("vypis.csv", io.BytesIO(content), "text/csv")},
        headers=headers,
    )


def test_statement_import_is_idempotent(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    first = import_statement(client, organizer)
    assert first.status_code == 200, first.text
    assert first.json() == {
        "new": 2, "duplicate": 0, "matched": 0, "flagged": 0, "unmatched": 2, "set_aside": 0
    }

    again = import_statement(client, organizer)
    assert again.json() == {
        "new": 0, "duplicate": 2, "matched": 0, "flagged": 0, "unmatched": 0, "set_aside": 0
    }

    listing = client.get("/api/tournaments/cup/payments/transactions", headers=organizer)
    assert len(listing.json()) == 2


def test_import_requires_organizer(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    outsider = auth_headers(email="x@example.com", name="X")
    assert import_statement(client, outsider).status_code == 403


class StubFio:
    def __init__(self, transactions):
        self.transactions = transactions
        self.calls = []

    def fetch(self, token, date_from, date_to):
        self.calls.append(token)
        return self.transactions


@pytest.fixture
def stub_fio():
    stub = StubFio(parse_fio_json(FIO_JSON))
    app.dependency_overrides[get_fio_client] = lambda: stub
    yield stub
    app.dependency_overrides.pop(get_fio_client, None)


def test_fio_poll_overlaps_with_csv_idempotently(client, auth_headers, stub_fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, fio_token="secret-token")

    import_statement(client, organizer)  # brings 26662142344 and ...46
    polled = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert polled.status_code == 200
    # ...44 already known from CSV; ...45 is new
    assert polled.json() == {
        "new": 1, "duplicate": 1, "matched": 0, "flagged": 0, "unmatched": 1, "set_aside": 0
    }
    assert stub_fio.calls == ["secret-token"]


def test_fio_poll_without_token(client, auth_headers, stub_fio):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    response = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "fio_token_not_configured"


def test_incoming_transaction_roundtrip_model():
    transaction = IncomingTransaction(
        external_id="1", date=datetime.date(2026, 1, 1), amount_cents=100, currency="CZK"
    )
    assert transaction.vs is None
