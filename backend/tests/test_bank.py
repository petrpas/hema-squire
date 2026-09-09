import datetime
import io

import httpx
import pytest

from app.bank import (
    FioTokenRejected,
    FioUnreachable,
    HttpFioClient,
    get_fio_client,
    parse_fio_csv,
    parse_fio_json,
)
from app.main import app
from tests.conftest import AcceptingFio, enable_payments, publish, set_fio_token, settle

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


def _verify_response(monkeypatch, *, status: int = 200, raises: Exception | None = None):
    """Point the real client's one outbound call at a canned answer. Verifying
    is the only place `HttpFioClient` decides anything, so it is tested against
    responses rather than through a stub of itself."""

    def fake_get(url, timeout=None):
        if raises is not None:
            raise raises
        return httpx.Response(status, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)


def test_verify_accepts_a_working_token(monkeypatch):
    _verify_response(monkeypatch, status=200)
    HttpFioClient().verify("good-token")  # returns rather than raising


def test_verify_rejects_a_token_fio_refuses(monkeypatch):
    _verify_response(monkeypatch, status=404)
    with pytest.raises(FioTokenRejected):
        HttpFioClient().verify("bad-token")


def test_verify_treats_an_unreachable_bank_as_no_evidence(monkeypatch):
    _verify_response(monkeypatch, raises=httpx.ConnectError("refused"))
    with pytest.raises(FioUnreachable):
        HttpFioClient().verify("good-token")


def test_verify_treats_fios_own_failure_as_no_evidence(monkeypatch):
    # a 500 is Fio's fault; accusing the organizer's token would be the worse
    # of the two errors
    _verify_response(monkeypatch, status=500)
    with pytest.raises(FioUnreachable):
        HttpFioClient().verify("good-token")


def test_verify_treats_the_rate_limit_as_no_evidence(monkeypatch):
    # one call per 30s per token: a 409 means Fio recognised the token well
    # enough to count it
    _verify_response(monkeypatch, status=409)
    with pytest.raises(FioUnreachable):
        HttpFioClient().verify("good-token")


def test_verify_ingests_nothing(monkeypatch, client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    _verify_response(monkeypatch, status=200)
    HttpFioClient().verify("good-token")
    outstanding = client.get("/api/tournaments/cup/payments/transactions", headers=organizer)
    assert outstanding.status_code == 200
    assert outstanding.json() == []


def setup_tournament(client, organizer, fio_token=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    # a discipline and a publish only so the tournament can take money at all:
    # payments wait for publication (spec tournament-publication), and a
    # tournament with nothing to enter cannot be published
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "cup")
    if fio_token:
        set_fio_token(client, organizer, "cup", fio_token)


def import_statement(client, headers, content=FIO_CSV):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("vypis.csv", io.BytesIO(content), "text/csv")},
        headers=headers,
    )


def test_statement_import_is_idempotent(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    # the import is a started operation now, so the counts live in its record
    first = import_statement(client, organizer)
    assert first.status_code == 202, first.text
    assert settle(client, organizer, kind="statement")["outcome"] == {
        "new": 2,
        "duplicate": 0,
        "matched": 0,
        "flagged": 0,
        "unmatched": 2,
        "partial": 0,
        "set_aside": 0,
        # intake issues before it matches; this roster is in-app, so it issues
        # nothing (spec payments-intake)
        "issued": 0,
        "already_issued": 0,
        "skipped": [],
    }

    import_statement(client, organizer)
    assert settle(client, organizer, kind="statement")["outcome"] == {
        "new": 0,
        "duplicate": 2,
        "matched": 0,
        "flagged": 0,
        "unmatched": 0,
        "partial": 0,
        "set_aside": 0,
        # intake issues before it matches; this roster is in-app, so it issues
        # nothing (spec payments-intake)
        "issued": 0,
        "already_issued": 0,
        "skipped": [],
    }

    listing = client.get("/api/tournaments/cup/payments/transactions", headers=organizer)
    assert len(listing.json()) == 2


def test_import_requires_organizer(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    outsider = auth_headers(email="x@example.com", name="X")
    assert import_statement(client, outsider).status_code == 403


class StubFio(AcceptingFio):
    def __init__(self, transactions):
        self.transactions = transactions
        self.calls = []
        self.verified = []

    def fetch(self, token, date_from, date_to):
        self.calls.append(token)
        return self.transactions

    def verify(self, token):
        self.verified.append(token)


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
        "new": 1,
        "duplicate": 1,
        "matched": 0,
        "flagged": 0,
        "unmatched": 1,
        "partial": 0,
        "set_aside": 0,
        # intake issues before it matches; this roster is in-app, so it issues
        # nothing (spec payments-intake)
        "issued": 0,
        "already_issued": 0,
        "skipped": [],
    }
    assert stub_fio.calls == ["secret-token"]


def test_fio_poll_without_token(client, auth_headers, stub_fio):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    response = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "fio_token_not_configured"


def test_fio_poll_refuses_an_unbounded_window(client, auth_headers, stub_fio):
    """`days_back` becomes `today - timedelta(days=days_back)`. Unbounded, a
    large enough int overflows the date and the request answered 500 rather
    than refusing the number (found by the contract fuzzer, static-analysis
    change phase 4)."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    refused = client.post(
        "/api/tournaments/cup/payments/fio-poll?days_back=999999999", headers=organizer
    )
    assert refused.status_code == 422
    assert stub_fio.calls == []
