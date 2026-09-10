import datetime
import io

import httpx
import pytest

from app.bank import (
    FioAuthorizationRequired,
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


def _verify_response(
    monkeypatch,
    *,
    status: int = 200,
    raises: Exception | None = None,
    body: str = "",
):
    """Point the real client's one outbound call at a canned answer. Reading
    the answer is where `HttpFioClient` decides anything, so both its methods
    are tested against responses rather than through a stub of themselves."""

    def fake_get(url, timeout=None):
        if raises is not None:
            raise raises
        return httpx.Response(status, text=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)


# what Fio answers for a window reaching further back than 90 days
OLDER_THAN_NINETY = (
    "Data není možné poskytnout bez silné autorizace. Pokyn k zobrazení dat si "
    "autorizujte ve Vašem Internetovém bankovnictví a data si vyžádejte znovu. "
    "Platnost ověření je 10 minut od autorizace. Nebo požádejte o data, která "
    "nejsou starší jak 90 dní (od 12.06.2026), v takovém případě není "
    "autorizace třeba."
)


def test_fetch_reads_a_422_as_the_history_lock(monkeypatch):
    # the token is good and the window is right: what is missing is the
    # organizer's strong authorization, so this is its own answer
    _verify_response(monkeypatch, status=422, body=OLDER_THAN_NINETY)
    with pytest.raises(FioAuthorizationRequired) as refusal:
        HttpFioClient().fetch("good-token", datetime.date(2026, 4, 1), datetime.date(2026, 5, 23))
    # Fio's own boundary, read from its answer rather than recomputed
    assert refusal.value.since == datetime.date(2026, 6, 12)


def test_fetch_falls_back_to_ninety_days_when_fio_names_no_date(monkeypatch):
    _verify_response(monkeypatch, status=422, body="silná autorizace")
    with pytest.raises(FioAuthorizationRequired) as refusal:
        HttpFioClient().fetch("good-token", datetime.date(2026, 4, 1), datetime.date(2026, 5, 23))
    today = datetime.datetime.now(datetime.UTC).date()
    assert refusal.value.since == today - datetime.timedelta(days=90)


def test_fetch_never_carries_the_token_into_a_failure(monkeypatch):
    # the token sits in the path, so an error quoting the URL would print it
    # into the log of whatever catches it
    _verify_response(monkeypatch, status=500, body="https://fioapi.fio.cz/v1/rest/periods/secret")
    with pytest.raises(FioUnreachable) as failure:
        HttpFioClient().fetch("secret", datetime.date(2026, 9, 1), datetime.date(2026, 9, 2))
    assert "secret" not in str(failure.value)


def test_fetch_reads_a_dead_connection_as_unreachable(monkeypatch):
    _verify_response(monkeypatch, raises=httpx.ConnectError("refused"))
    with pytest.raises(FioUnreachable):
        HttpFioClient().fetch("good-token", datetime.date(2026, 9, 1), datetime.date(2026, 9, 2))


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
    # the statement's second row is a refund out of the account, dropped at
    # ingestion as nobody's entry fee, and counted as neither new nor duplicate
    assert settle(client, organizer, kind="statement")["outcome"] == {
        "new": 1,
        "duplicate": 0,
        "dropped": 1,
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

    import_statement(client, organizer)
    assert settle(client, organizer, kind="statement")["outcome"] == {
        "new": 0,
        "duplicate": 1,
        "dropped": 1,
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
    assert len(listing.json()) == 1


def test_import_requires_organizer(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    outsider = auth_headers(email="x@example.com", name="X")
    assert import_statement(client, outsider).status_code == 403


class StubFio(AcceptingFio):
    def __init__(self, transactions):
        self.transactions = transactions
        self.calls = []
        self.windows = []
        self.verified = []

    def fetch(self, token, date_from, date_to):
        self.calls.append(token)
        self.windows.append((date_from, date_to))
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

    # brings 26662142344; ...46 is a refund out of the account and is dropped
    import_statement(client, organizer)
    polled = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert polled.status_code == 200
    # ...44 already known from CSV; ...45 is new
    assert polled.json() == {
        "new": 1,
        "duplicate": 1,
        "dropped": 0,
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


class RefusingFio(AcceptingFio):
    def __init__(self, refusal):
        self.refusal = refusal

    def fetch(self, token, date_from, date_to):
        raise self.refusal


def _poll_against(client, auth_headers, refusal):
    organizer = auth_headers()
    setup_tournament(client, organizer, fio_token="secret-token")
    app.dependency_overrides[get_fio_client] = lambda: RefusingFio(refusal)
    try:
        return client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    finally:
        app.dependency_overrides.pop(get_fio_client, None)


def test_poll_states_the_history_lock_rather_than_failing(client, auth_headers):
    # the console has to be able to say which days are behind the lock, so the
    # date the bank named survives the trip
    response = _poll_against(
        client, auth_headers, FioAuthorizationRequired(datetime.date(2026, 6, 12))
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "fio_authorization_required"
    assert response.json()["detail"]["since"] == "2026-06-12"


def test_poll_carries_the_window_beside_the_lock(client, auth_headers):
    # what the console can offer depends on whether the window and the bank's
    # ninety days overlap, so both travel with the refusal
    response = _poll_against(
        client, auth_headers, FioAuthorizationRequired(datetime.date(2026, 6, 12))
    )
    detail = response.json()["detail"]
    assert detail["window_from"] and detail["window_to"]


def _with_open_window(client, organizer):
    """A tournament whose poll window spans months rather than the one day a
    freshly published tournament's does — the only shape a shortened window
    says anything about."""
    setup_tournament(client, organizer, fio_token="secret-token")
    client.patch(
        "/api/tournaments/cup",
        json={"registration_opens": "2026-04-01"},
        headers=organizer,
    )


def test_poll_from_a_later_day_asks_the_bank_for_that_day(client, auth_headers, stub_fio):
    organizer = auth_headers()
    _with_open_window(client, organizer)

    response = client.post(
        "/api/tournaments/cup/payments/fio-poll?since=2026-06-12", headers=organizer
    )

    assert response.status_code == 200
    assert stub_fio.windows[-1][0] == datetime.date(2026, 6, 12)


def test_poll_from_a_later_day_never_widens_the_window(client, auth_headers, stub_fio):
    # a start before the window's own is not this tournament's to ask about
    organizer = auth_headers()
    _with_open_window(client, organizer)

    client.post("/api/tournaments/cup/payments/fio-poll?since=2020-01-01", headers=organizer)

    assert stub_fio.windows[-1][0] == datetime.date(2026, 4, 1)


def test_poll_refuses_a_start_past_the_window(client, auth_headers, stub_fio):
    # answering "nothing found" would say the bank had been asked
    organizer = auth_headers()
    setup_tournament(client, organizer, fio_token="secret-token")
    tomorrow = datetime.datetime.now(datetime.UTC).date() + datetime.timedelta(days=1)

    response = client.post(
        f"/api/tournaments/cup/payments/fio-poll?since={tomorrow.isoformat()}", headers=organizer
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "poll_window_empty"
    assert stub_fio.windows == []


def test_poll_reports_an_unreachable_bank_as_the_bank(client, auth_headers):
    response = _poll_against(client, auth_headers, FioUnreachable("500"))
    assert response.status_code == 502
    assert response.json()["detail"] == {"code": "fio_unreachable"}


def test_fio_poll_without_token(client, auth_headers, stub_fio):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    response = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "fio_token_not_configured"


def test_the_poll_window_is_not_a_caller_s_to_choose(client, auth_headers, stub_fio):
    """The window is the tournament's own and no parameter steers it.

    It used to be `days_back`, a rolling fortnight a caller could widen, and
    `today - timedelta(days=days_back)` is what it became: unbounded, a large
    enough int overflowed the date and the request answered 500 rather than
    refusing the number (found by the contract fuzzer). Bounding the parameter
    fixed the overflow; removing it removes the arithmetic, and with it the
    rolling fortnight that was asking the wrong question to begin with.
    """
    organizer = auth_headers()
    setup_tournament(client, organizer, fio_token="secret-token")
    client.patch(
        "/api/tournaments/cup",
        json={"registration_opens": "2026-04-01", "date": "2026-05-23"},
        headers=organizer,
    )

    polled = client.post(
        "/api/tournaments/cup/payments/fio-poll?days_back=999999999", headers=organizer
    )

    assert polled.status_code == 200
    # the number is ignored: the bank was asked about the tournament's window
    assert [(str(a), str(b)) for a, b in stub_fio.windows] == [("2026-04-01", "2026-05-23")]
