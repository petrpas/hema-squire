import io

import pytest

from app.mail import get_mailer
from app.main import app
from tests.conftest import publish


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


CSV = (
    "meta;data\n\n"
    "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
    "77;01.08.2026;2 000,00;CZK;;;;platba za dva;Klubový účet;123\n"
).encode()


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
    publish(client, organizer, "cup")


def enroll(client, auth_headers, email, name):
    headers = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201
    return headers, response.json()["vs"]


def import_csv(client, organizer):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(CSV), "text/csv")},
        headers=organizer,
    ).json()


def unmatched_transaction_id(client, organizer):
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    return queue[0]["id"]


def state_of(client, headers):
    return client.get("/api/tournaments/cup/my-registration", headers=headers).json()["state"]


def test_one_transfer_covers_two_fencers(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")

    assert import_csv(client, organizer)["unmatched"] == 1
    transaction_id = unmatched_transaction_id(client, organizer)
    mailbox.sent.clear()

    linked = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a, vs_b]},
        headers=organizer,
    )
    assert linked.status_code == 201, linked.text

    assert state_of(client, fencer_a) == "paid"
    assert state_of(client, fencer_b) == "paid"
    assert len(mailbox.sent) == 2  # both fencers got payment confirmations

    statuses = {p["name"]: p["status"] for p in
                client.get("/api/tournaments/cup/participants").json()}
    assert statuses == {"Adéla": "confirmed", "Boris": "confirmed"}

    # persisted as a rule in the payments phase
    listed = client.get(
        "/api/tournaments/cup/rules", params={"phase": "payments"}, headers=organizer
    ).json()
    assert listed[0]["kind"] == "payment_link"
    # the amount credited per VS is recorded at apply time (design Decision 7)
    assert listed[0]["payload"] == {
        "vs": [vs_a, vs_b],
        "credited": {str(vs_a): 100000, str(vs_b): 100000},
    }


def test_link_survives_reingestion(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    import_csv(client, organizer)
    transaction_id = unmatched_transaction_id(client, organizer)
    client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a]},
        headers=organizer,
    )
    mailbox.sent.clear()

    result = import_csv(client, organizer)  # overlapping re-import
    assert result["duplicate"] == 1
    assert state_of(client, fencer_a) == "paid"
    assert mailbox.sent == []  # no duplicate confirmation


def test_removing_link_rule_reverts(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    import_csv(client, organizer)
    transaction_id = unmatched_transaction_id(client, organizer)
    rule_id = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a]},
        headers=organizer,
    ).json()["rule_id"]
    assert state_of(client, fencer_a) == "paid"

    delete = client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)
    assert delete.status_code == 204

    assert state_of(client, fencer_a) == "reserved"
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert [t["id"] for t in queue] == [transaction_id]
    assert queue[0]["status_reason"] == "manual_unlink"


def test_auto_matched_registration_not_reverted_by_unlink(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")

    auto_csv = (
        "meta;x\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        f"88;01.08.2026;1 000,00;CZK;{vs_a};;;;;\n"
        "77;01.08.2026;500,00;CZK;;;;dar;;\n"
    ).encode()
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(auto_csv), "text/csv")},
        headers=organizer,
    )
    assert state_of(client, fencer_a) == "paid"  # auto-matched via VS

    # organizer mistakenly links the unrelated donation to the same VS, then removes it
    transaction_id = unmatched_transaction_id(client, organizer)
    rule_id = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a]},
        headers=organizer,
    ).json()["rule_id"]
    client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)

    # the auto-match keeps the registration paid
    assert state_of(client, fencer_a) == "paid"


def test_manual_link_distributes_without_overpaying(client, auth_headers, mailbox):
    """A 3500 transfer covering two registrations owing 1750 each credits
    1750 to each — not the full 3500 to both (design Decision 7)."""
    organizer = auth_headers()
    setup(client, organizer)
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"code": "LS", "capacity": 10, "fee": 1750},
        headers=organizer,
    )
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")

    csv = (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        "77;01.08.2026;3 500,00;CZK;;;;platba za dva;Klubový účet;123\n"
    ).encode()
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=organizer,
    )
    transaction_id = unmatched_transaction_id(client, organizer)
    client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a, vs_b]},
        headers=organizer,
    )

    reg_a = client.get("/api/tournaments/cup/my-registration", headers=fencer_a).json()
    reg_b = client.get("/api/tournaments/cup/my-registration", headers=fencer_b).json()
    assert reg_a["state"] == "paid" and reg_b["state"] == "paid"
    assert reg_a["outstanding_amount"] == "0.00"
    assert reg_b["outstanding_amount"] == "0.00"
    assert reg_a["refund_state"] == "not_applicable"
    assert reg_b["refund_state"] == "not_applicable"


def test_removing_distributed_link_reverts_exact_amounts(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)  # fee 1000
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"code": "LS", "capacity": 10, "fee": 2000},
        headers=organizer,
    )
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")

    csv = (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        "77;01.08.2026;3 000,00;CZK;;;;platba za dva;Klubový účet;123\n"
    ).encode()
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=organizer,
    )
    transaction_id = unmatched_transaction_id(client, organizer)
    rule_id = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs_a, vs_b]},
        headers=organizer,
    ).json()["rule_id"]
    assert state_of(client, fencer_a) == "paid"
    assert state_of(client, fencer_b) == "paid"

    delete = client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)
    assert delete.status_code == 204

    reg_a = client.get("/api/tournaments/cup/my-registration", headers=fencer_a).json()
    reg_b = client.get("/api/tournaments/cup/my-registration", headers=fencer_b).json()
    assert reg_a["state"] == "reserved" and reg_b["state"] == "reserved"
    # exactly what was credited comes back off — not more, not less
    assert reg_a["outstanding_amount"] == "1000.00"
    assert reg_b["outstanding_amount"] == "2000.00"


def test_link_validation(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Adéla")
    import_csv(client, organizer)
    transaction_id = unmatched_transaction_id(client, organizer)

    unknown = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [9999999]},
        headers=organizer,
    )
    assert unknown.status_code == 404

    missing = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": 424242, "vs": [1000001]},
        headers=organizer,
    )
    assert missing.status_code == 404
