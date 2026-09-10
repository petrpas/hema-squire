"""Re-deciding a short payment when the tolerance widens (spec `payments`).

The tolerance used to reach only payments that had not arrived yet: raising it
because a transfer came up five crowns short did nothing to that transfer, and
the console said so in words nobody could act on. Widening it now re-asks the
one question the tolerance answers, over the payments it already answered it
for.

What matters here is what the pass does *not* do. It moves no money — the
credit happened when the payment arrived — it reaches nothing outside the
`partial` record it made itself, and narrowing the tolerance takes nothing
back.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import BankTransaction, Registration, RegistrationState
from tests.conftest import credit_registration
from tests.test_matching import (
    CollectingMailer,
    db_session,
    enroll,
    import_rows,
    local_midnight,
    paid_at_of,
    registration_by_vs,
    setup,
)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def set_tolerance(client, organizer, percent, slug="cup"):
    response = client.patch(
        f"/api/tournaments/{slug}",
        json={"amount_tolerance_percent": percent},
        headers=organizer,
    )
    assert response.status_code == 200


def countable(client, organizer, slug="cup"):
    return client.get(f"/api/tournaments/{slug}/payments/resettle", headers=organizer)


def resettle(client, organizer, slug="cup"):
    return client.post(f"/api/tournaments/{slug}/payments/resettle", headers=organizer)


def transactions():
    return list(db_session().scalars(select(BankTransaction)))


def short_payment(client, auth_headers, organizer, email="jan@example.com"):
    """A fencer owing 1000 who sent 995, against a tournament that tolerates
    nothing — so the payment is credited and the reservation stays reserved."""
    set_tolerance(client, organizer, 0)
    fencer, vs = enroll(client, auth_headers, email=email, name=email.split("@")[0])
    import_rows(client, organizer, [f"1;01.08.2026;995,00;CZK;{vs};;;;;"])
    assert transactions()[0].status == "partial"
    return fencer, vs


def test_a_widened_tolerance_settles_a_short_payment(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = short_payment(client, auth_headers, organizer)

    # stated before it is done, so the organizer commits to a number
    set_tolerance(client, organizer, 5)
    assert countable(client, organizer).json() == {"resettleable": 1}

    assert resettle(client, organizer).json() == {"settled": 1}
    assert registration_by_vs(vs).state == RegistrationState.RESERVED


def test_it_moves_no_money(client, auth_headers, mailbox):
    """The credit happened when the payment arrived. Only the verdict on
    whether it was close enough is asked again, so the amount recorded against
    the registration is the same before and after."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = short_payment(client, auth_headers, organizer)
    before = registration_by_vs(vs).credited_in("local")

    set_tolerance(client, organizer, 5)
    resettle(client, organizer)

    after = registration_by_vs(vs)
    assert after.credited_in("local") == before == 99500
    # and the transaction stops claiming to be a shortfall, saying why
    assert transactions()[0].status == "matched"
    assert transactions()[0].status_reason == "tolerance_widened"


def test_narrowing_the_tolerance_takes_nothing_back(client, auth_headers, mailbox):
    """Squire has told the fencer they are paid. A percentage field does not
    undo that on its own — the tightened tolerance applies to what comes
    next."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = short_payment(client, auth_headers, organizer)
    set_tolerance(client, organizer, 5)
    resettle(client, organizer)
    assert registration_by_vs(vs).state == RegistrationState.RESERVED

    set_tolerance(client, organizer, 0)

    assert countable(client, organizer).json() == {"resettleable": 0}
    assert resettle(client, organizer).json() == {"settled": 0}
    assert registration_by_vs(vs).state == RegistrationState.RESERVED


def test_it_reaches_nothing_the_tolerance_did_not_decide(client, auth_headers, mailbox):
    """An unmatched payment is not waiting on a tolerance: nobody has read it
    against a registration yet. Widening the tolerance must not credit it."""
    organizer = auth_headers()
    setup(client, organizer)
    set_tolerance(client, organizer, 0)
    import_rows(client, organizer, ["1;01.08.2026;995,00;CZK;9999999;;;;;"])
    assert transactions()[0].status == "unmatched"

    set_tolerance(client, organizer, 90)

    assert countable(client, organizer).json() == {"resettleable": 0}
    assert resettle(client, organizer).json() == {"settled": 0}
    assert transactions()[0].status == "unmatched"


def test_an_uncredited_shortfall_is_not_swept_in(client, auth_headers, mailbox):
    """The load-bearing distinction. A bare token in the message with the wrong
    amount is refused *before* anything is credited — a bare token can never
    create a partial payment — so widening the tolerance would have to credit
    money nobody has looked at. It does not: this pass re-decides verdicts on
    payments already taken in, and takes none in.
    """
    organizer = auth_headers()
    setup(client, organizer)
    set_tolerance(client, organizer, 0)
    _, vs = enroll(client, auth_headers)
    # the token sits in the message, not the VS field, so it is an inference
    import_rows(client, organizer, [f"1;01.08.2026;995,00;CZK;;;;{vs};;"])
    assert transactions()[0].status == "unmatched"
    assert transactions()[0].status_reason == "bare_vs_amount_mismatch"
    assert registration_by_vs(vs).credited_in("local") == 0

    set_tolerance(client, organizer, 5)

    assert countable(client, organizer).json() == {"resettleable": 0}
    assert resettle(client, organizer).json() == {"settled": 0}
    assert registration_by_vs(vs).credited_in("local") == 0
    assert registration_by_vs(vs).state == RegistrationState.RESERVED


def test_the_fencer_is_told(client, auth_headers, mailbox):
    """Becoming paid is the same event however it was reached, so it sends the
    same notice as a payment that settled on arrival."""
    organizer = auth_headers()
    setup(client, organizer)
    short_payment(client, auth_headers, organizer)
    set_tolerance(client, organizer, 5)
    mailbox.sent.clear()

    resettle(client, organizer)

    assert len(mailbox.sent) == 1
    assert "částečnou" not in mailbox.sent[-1]["Subject"]


def test_a_registration_settled_otherwise_is_left_alone(client, auth_headers, mailbox):
    """Paid by other means since. Re-deciding it here would overwrite an answer
    something else already gave."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = short_payment(client, auth_headers, organizer)
    registration = registration_by_vs(vs)
    session = db_session()
    row = session.get(Registration, registration.id)
    credit_registration(session, row, row.total_amount * 100)

    set_tolerance(client, organizer, 5)

    assert countable(client, organizer).json() == {"resettleable": 0}
    assert resettle(client, organizer).json() == {"settled": 0}


def test_refused_without_console_access(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    short_payment(client, auth_headers, organizer)
    set_tolerance(client, organizer, 5)
    stranger = auth_headers(email="nobody@example.com", name="Nobody")

    assert resettle(client, stranger).status_code in (401, 403, 404)
    assert transactions()[0].status == "partial"


def test_refused_where_payments_are_disabled(client, auth_headers, mailbox):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "nopay", "display_name": "No Pay", "date": "2026-12-05"},
        headers=organizer,
    )

    assert countable(client, organizer, "nopay").status_code == 409
    assert resettle(client, organizer, "nopay").status_code == 409


def test_the_settlement_is_dated_to_the_transaction_not_to_the_widening(
    client, auth_headers, mailbox
):
    """The money arrived on the 1st; the organizer widened the tolerance
    weeks later. The registration is dated to the money, and the organizer's
    act is recorded where decisions are recorded — as the transaction's reason
    and as an event (design paid-at-is-value-date D4)."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = short_payment(client, auth_headers, organizer)

    set_tolerance(client, organizer, 5)
    assert resettle(client, organizer).json() == {"settled": 1}

    assert paid_at_of(vs) == local_midnight(date(2026, 8, 1))
    assert transactions()[0].status_reason == "tolerance_widened"
