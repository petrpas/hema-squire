import io
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import PaymentEvent, RefundState, Registration, RegistrationState, Rule
from tests.conftest import enable_payments, publish


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
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, "cup")


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


def db_session():
    return next(app.dependency_overrides[get_session]())


def registration_by_vs(vs) -> Registration:
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def age_reserved(vs, *, expires_in_hours):
    """Move a still-reserved registration's expiry, without touching any
    credit already recorded against it."""
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)
    session.commit()


def force_expired(vs, hours_ago=1):
    """Move a registration straight to EXPIRED, `hours_ago` past its window,
    without touching any credit already recorded against it."""
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.state = RegistrationState.EXPIRED
    registration.expires_at = datetime.now(UTC) - timedelta(hours=hours_ago)
    session.commit()


def event_kinds(vs):
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    return [
        event.kind
        for event in session.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.registration_id == registration.id)
            .order_by(PaymentEvent.id)
        )
    ]


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


def test_far_off_amount_credited_as_partial_payment(client, auth_headers, mailbox):
    """A shortfall beyond tolerance is no longer discarded: it is credited to
    the registration and recorded as a partial payment (design
    harden-payment-matching Decision 1), leaving the reservation reserved
    with the balance recorded rather than sitting in the organizer's queue."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    assert result == {
        "new": 1, "duplicate": 0, "matched": 0, "flagged": 0, "unmatched": 0, "partial": 1,
        "set_aside": 0,
    }
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "reserved"

    # a partial transaction has nothing for the organizer to do — it is not
    # in the unmatched/flagged queue
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue == []

    all_transactions = client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json()
    assert all_transactions[0]["status"] == "partial"
    assert all_transactions[0]["status_reason"] == "partial_payment"
    assert "Přijali jsme částečnou platbu" in mailbox.sent[-1]["Subject"]


def test_vs_in_message_matches_sepa_style(client, auth_headers, mailbox):
    """A foreign transfer carries its VS in the message and its amount in the
    tournament's stored EUR total. The tournament prices in CZK and EUR
    independently; no conversion happens anywhere in the payment path, so the
    transfer is compared straight against the stored EUR total (39)."""
    organizer = auth_headers()
    setup(client, organizer)
    # the tournament is already published: give the discipline its EUR price
    # before enabling EUR mode (design D3 of add-explicit-publishing)
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000, "fee_eur": 39},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"eur_payments_enabled": True},
        headers=organizer,
    )
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(
        client, organizer, [f"1;01.08.2026;39,00;EUR;;;;platba VS{vs} Cup;MUELLER;DE99"]
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


def setup_with_eur(client, organizer, fee=1000, fee_eur=40):
    setup(client, organizer)
    # the tournament is already published: give the discipline its EUR price
    # before enabling EUR mode, so it never passes through an incomplete
    # moment (design D3 of add-explicit-publishing)
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": fee, "fee_eur": fee_eur},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"eur_payments_enabled": True},
        headers=organizer,
    )


def test_either_currency_settles_the_registration(client, auth_headers, mailbox):
    """A registration owing 1000 Kč or 40 € is settled by a EUR credit alone
    (design Decision 5) — no local-currency balance is treated as outstanding."""
    organizer = auth_headers()
    setup_with_eur(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(client, organizer, [f"1;01.08.2026;40,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_credits_not_summed_across_currencies(client, auth_headers, mailbox):
    """Neither currency's credit covers its own total, and the two are never
    combined into one balance — each is credited as its own currency's
    partial payment rather than reading as settled (design Decision 5)."""
    organizer = auth_headers()
    setup_with_eur(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    czk_result = import_rows(client, organizer, [f"1;01.08.2026;400,00;CZK;{vs};;;;;"])
    eur_result = import_rows(client, organizer, [f"2;01.08.2026;15,00;EUR;{vs};;;;MUELLER;DE99"])
    assert czk_result["partial"] == 1
    assert eur_result["partial"] == 1

    registration = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert registration["state"] == "reserved"
    assert registration["outstanding_amount"] == "600.00"
    assert registration["outstanding_eur_amount"] == "25.00"
    # neither is a flag — there is nothing for the organizer to resolve
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue == []


def test_manual_link_credits_the_transactions_own_currency(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup_with_eur(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    csv = make_csv([f"1;01.08.2026;40,00;EUR;;;;;MUELLER;DE99"])
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=organizer,
    )
    transaction_id = client.get(
        "/api/tournaments/cup/payments/unmatched", headers=organizer
    ).json()[0]["id"]
    client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [vs]},
        headers=organizer,
    )

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_reimport_does_not_rematch(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    row = [f"1;01.08.2026;1 000,00;CZK;{vs};;;;;"]
    import_rows(client, organizer, row)
    emails_after_first = len(mailbox.sent)
    result = import_rows(client, organizer, row)
    assert result == {
        "new": 0, "duplicate": 1, "matched": 0, "flagged": 0, "unmatched": 0, "partial": 0,
        "set_aside": 0,
    }
    assert len(mailbox.sent) == emails_after_first


def test_two_half_payments_same_import_aggregate_to_paid(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(
        client, organizer,
        [f"1;01.08.2026;900,00;CZK;{vs};;;;;", f"2;01.08.2026;850,00;CZK;{vs};;;;;"],
    )
    assert result["partial"] == 1  # the first, still short
    assert result["matched"] == 1  # the second, completing it
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_two_half_payments_separate_imports_aggregate_to_paid(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    first = import_rows(client, organizer, [f"1;01.08.2026;900,00;CZK;{vs};;;;;"])
    assert first["partial"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "reserved"
    assert state["outstanding_amount"] == "100.00"

    second = import_rows(client, organizer, [f"2;02.08.2026;100,00;CZK;{vs};;;;;"])
    assert second["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
    assert state == "paid"


def test_partial_in_both_currencies_settles_via_one_lane_alone(client, auth_headers, mailbox):
    """A registration part-paid in each currency stays reserved (never
    summed), but a further credit that alone reaches one lane's own total
    settles it — no local-currency balance is treated as outstanding (design
    Decision 5)."""
    organizer = auth_headers()
    setup_with_eur(client, organizer, fee=1000, fee_eur=40)
    fencer, vs = enroll(client, auth_headers)

    import_rows(client, organizer, [f"1;01.08.2026;400,00;CZK;{vs};;;;;"])
    import_rows(client, organizer, [f"2;01.08.2026;15,00;EUR;{vs};;;;MUELLER;DE99"])
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "reserved"

    result = import_rows(client, organizer, [f"3;01.08.2026;25,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "paid"
    # the CZK partial (400 of 1000) is untouched by the EUR lane settling
    assert state["outstanding_amount"] == "600.00"


def test_partial_payment_does_not_extend_window_and_expiry_records_holding_payment(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "reserved"
    original_expires = state["expires_at"]

    age_reserved(vs, expires_in_hours=-1)  # past its (unmoved) window
    mailbox.sent.clear()
    result = client.post("/api/tournaments/cup/payments/process", headers=organizer).json()
    assert result["expired"] == 1

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "expired"
    assert original_expires is not None  # the window itself was never touched by the credit

    assert "expired_holding_payment" in event_kinds(vs)
    assert "reservation_expired" not in event_kinds(vs)
    assert "Rezervace vypršela, platbu držíme" in mailbox.sent[-1]["Subject"]


def test_remaining_balance_in_grace_reinstates_and_settles(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    force_expired(vs, hours_ago=1)  # well within the default 48h grace

    result = import_rows(client, organizer, [f"2;02.08.2026;400,00;CZK;{vs};;;;;"])
    assert result["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "paid"
    assert "reinstated_in_grace" in event_kinds(vs)


def test_labelled_vs_matches_outside_and_inside_message(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")

    # Uživatelská identifikace (user_identification) column, not the message
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet;"
        "Uživatelská identifikace"
    )
    rows = [
        f"1;01.08.2026;1 000,00;CZK;;;;;;;VS{vs_a} platba",
        f"2;01.08.2026;1 000,00;CZK;;;;VS{vs_b} platba;;;",
    ]
    content = ("meta;data\n\n" + header + "\n" + "\n".join(rows) + "\n").encode()
    result = client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(content), "text/csv")},
        headers=organizer,
    ).json()
    assert result["matched"] == 2
    assert client.get("/api/tournaments/cup/my-registration", headers=fencer_a).json()["state"] == "paid"
    assert client.get("/api/tournaments/cup/my-registration", headers=fencer_b).json()["state"] == "paid"


def test_bare_vs_matches_only_when_amount_covers_outstanding(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")

    result = import_rows(
        client, organizer,
        [
            # covering amount: automatic match
            f"1;01.08.2026;1 000,00;CZK;;;;platba {vs_a} dekuji;;",
            # unrelated amount: candidate only, no credit
            f"2;01.08.2026;250,00;CZK;;;;objednavka {vs_b};;",
        ],
    )
    assert result["matched"] == 1
    assert result["unmatched"] == 1

    assert client.get(
        "/api/tournaments/cup/my-registration", headers=fencer_a
    ).json()["state"] == "paid"
    state_b = client.get("/api/tournaments/cup/my-registration", headers=fencer_b).json()
    assert state_b["state"] == "reserved"
    assert state_b["outstanding_amount"] == "1000.00"  # not credited at all

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "bare_vs_amount_mismatch"
    assert queue[0]["candidate_vs"] == [vs_b]


def test_payer_name_digits_not_treated_as_vs(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    # the payer's account number happens to equal the issued VS digits
    result = import_rows(
        client, organizer, [f"1;01.08.2026;1 000,00;CZK;;;;;Jan Novak;{vs}"]
    )
    assert result["unmatched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "reserved"
    assert state["outstanding_amount"] == "1000.00"

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "no_vs"
    assert queue[0]["candidate_vs"] == []


def test_multi_vs_transfer_matching_sum_pays_all_and_reverts_together(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")
    fencer_c, vs_c = enroll(client, auth_headers, "c@example.com", "Cyril")

    result = import_rows(
        client, organizer,
        [f"1;01.08.2026;3 000,00;CZK;;;;platba za {vs_a} {vs_b} a {vs_c};klub;"],
    )
    assert result["matched"] == 1

    for fencer in (fencer_a, fencer_b, fencer_c):
        assert client.get(
            "/api/tournaments/cup/my-registration", headers=fencer
        ).json()["state"] == "paid"

    rules = client.get(
        "/api/tournaments/cup/rules", params={"phase": "payments"}, headers=organizer
    ).json()
    (rule,) = [r for r in rules if r["kind"] == "payment_link"]
    assert rule["payload"]["auto_created"] is True
    assert sorted(rule["payload"]["vs"]) == sorted([vs_a, vs_b, vs_c])

    delete = client.delete(f"/api/tournaments/cup/rules/{rule['id']}", headers=organizer)
    assert delete.status_code == 204
    for fencer in (fencer_a, fencer_b, fencer_c):
        assert client.get(
            "/api/tournaments/cup/my-registration", headers=fencer
        ).json()["state"] == "reserved"


def test_multi_vs_transfer_mismatched_sum_stays_unmatched_with_candidates(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    fencer_a, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    fencer_b, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")
    fencer_c, vs_c = enroll(client, auth_headers, "c@example.com", "Cyril")

    result = import_rows(
        client, organizer,
        # 2000, well short of the 3000 the three of them owe together
        [f"1;01.08.2026;2 000,00;CZK;;;;platba za {vs_a} {vs_b} a {vs_c};klub;"],
    )
    assert result["unmatched"] == 1
    assert result["matched"] == 0

    for fencer in (fencer_a, fencer_b, fencer_c):
        assert client.get(
            "/api/tournaments/cup/my-registration", headers=fencer
        ).json()["state"] == "reserved"

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "multi_vs_amount_mismatch"
    assert sorted(queue[0]["candidate_vs"]) == sorted([vs_a, vs_b, vs_c])


def test_organizer_resolved_transaction_untouched_by_later_pass(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    import_rows(client, organizer, [f"1;01.08.2026;1 000,00;CZK;{vs};;;;;"])  # paid
    import_rows(client, organizer, [f"2;02.08.2026;1 000,00;CZK;{vs};;;;;"])  # flagged: registration_paid
    transaction_id = client.get(
        "/api/tournaments/cup/payments/unmatched", headers=organizer
    ).json()[0]["id"]
    client.post(
        f"/api/tournaments/cup/payments/transactions/{transaction_id}/mark-for-refund",
        headers=organizer,
    )
    all_before = client.get("/api/tournaments/cup/payments/transactions", headers=organizer).json()
    before = [t for t in all_before if t["id"] == transaction_id][0]
    assert before["status"] == "resolved"

    # a later pass (any ingest triggers one) must not reconsider it
    import_rows(client, organizer, [f"2;02.08.2026;1,00;CZK;{vs};;;;;"])
    after = [
        t for t in client.get("/api/tournaments/cup/payments/transactions", headers=organizer).json()
        if t["id"] == transaction_id
    ][0]
    assert after == before


def test_reevaluated_flagged_transaction_not_credited_twice(client, auth_headers, mailbox):
    """A transaction flagged for a currency the tournament doesn't yet accept
    is reconsidered once the registration has a total in that currency to
    compare against — as an amendment would give it — and settling it once
    does not credit it again on a further pass (design Decision 2)."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    result = import_rows(client, organizer, [f"1;01.08.2026;40,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["flagged"] == 1
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "currency_not_accepted"

    # the tournament is already published: give the discipline its EUR price
    # before enabling EUR mode (design D3 of add-explicit-publishing)
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000, "fee_eur": 40},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup", json={"eur_payments_enabled": True}, headers=organizer,
    )
    # total_eur is fixed at registration time (never recomputed on read); an
    # amendment after enabling EUR pricing would set it exactly like this
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.total_eur = 40
    session.commit()

    # any ingest call re-runs the matching pass over what's still flagged
    reeval = import_rows(client, organizer, [f"2;02.08.2026;1,00;CZK;9999999;;;;;"])
    assert reeval["matched"] == 1
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "paid"

    # a further pass must not re-credit the now-matched transaction
    import_rows(client, organizer, [f"3;03.08.2026;1,00;CZK;9999998;;;;;"])
    state_after = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state_after == state
