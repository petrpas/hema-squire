import io

import pytest

from app.mail import get_mailer
from app.main import app


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def make_csv(rows):
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    )
    return ("meta;data\n\n" + header + "\n" + "\n".join(rows) + "\n").encode()


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
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )


def enroll(client, auth_headers, email="jan@example.com", name="Jan"):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201
    return fencer, response.json()["vs"]


def import_rows(client, organizer, rows):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(make_csv(rows)), "text/csv")},
        headers=organizer,
    ).json()


def test_exact_vs_match_marks_paid_and_notifies(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(client, organizer, [f"1;01.08.2026;1 000,00;CZK;{vs};;;;Jan N;123"])
    assert result["matched"] == 1

    registration = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert registration["state"] == "paid"
    participants = client.get("/api/tournaments/cup/participants").json()
    assert participants[0]["status"] == "confirmed"
    assert "Platba přijata" in mailbox.sent[-1]["Subject"]


def test_within_tolerance_accepted(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    # 3 % short (foreign conversion noise) — within the default ±5 %
    result = import_rows(client, organizer, [f"1;01.08.2026;970,00;CZK;{vs};;;;;"])
    assert result["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_far_off_amount_flagged_not_accepted(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    assert result == {"new": 1, "duplicate": 0, "matched": 0, "flagged": 1, "unmatched": 0}
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "reserved"

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "amount_out_of_tolerance"


def test_vs_in_message_matches_sepa_style(client, auth_headers, mailbox):
    """A foreign transfer carries its VS in the message and its amount in EUR;
    the tournament prices in CZK and takes EUR at a configured rate, so the
    amount is converted before the tolerance check (1000 CZK / 25.5 = 39.22)."""
    organizer = auth_headers()
    setup(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"eur_payments_enabled": True, "eur_rate": "25.5"},
        headers=organizer,
    )
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(
        client, organizer, [f"1;01.08.2026;39,22;EUR;;;;platba VS{vs} Cup;MUELLER;DE99"]
    )
    assert result["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_unknown_and_missing_vs_land_in_unmatched_queue(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)

    result = import_rows(
        client,
        organizer,
        ["1;01.08.2026;1 000,00;CZK;9999999;;;;;", "2;01.08.2026;500,00;CZK;;;;dar;;"],
    )
    assert result["matched"] == 0
    assert result["unmatched"] == 2

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    reasons = {t["external_id"]: t["status_reason"] for t in queue}
    assert reasons == {"1": "unknown_vs", "2": "no_vs"}


def test_second_payment_for_paid_registration_flagged(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    import_rows(client, organizer, [f"1;01.08.2026;1 000,00;CZK;{vs};;;;;"])
    result = import_rows(client, organizer, [f"2;02.08.2026;1 000,00;CZK;{vs};;;;;"])
    assert result["flagged"] == 1

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "registration_paid"


def test_reimport_does_not_rematch(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    row = [f"1;01.08.2026;1 000,00;CZK;{vs};;;;;"]
    import_rows(client, organizer, row)
    emails_after_first = len(mailbox.sent)
    result = import_rows(client, organizer, row)
    assert result == {"new": 0, "duplicate": 1, "matched": 0, "flagged": 0, "unmatched": 0}
    assert len(mailbox.sent) == emails_after_first
