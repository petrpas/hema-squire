"""Composition of fencer-facing emails, localized to the tournament's
communication language."""

from __future__ import annotations

import datetime
from decimal import ROUND_HALF_UP, Decimal
from email.message import EmailMessage
from typing import TYPE_CHECKING, Literal

from app import accounts, managekey, pricing, setup, spayd
from app.config import settings
from app.i18n import format_date, format_money, t
from app.mail import Mailer, build_message
from app.models import (
    Currency,
    Fencer,
    PaymentMode,
    PendingSignup,
    Registration,
    Tournament,
)
from app.setup import local_date

if TYPE_CHECKING:  # a substitution reaches its mail, and mail is not part of it
    from app.substitution import Prepared


def _summary_lines(
    registration: Registration,
    tournament: Tournament,
    lang: str,
    waits_for: list[str] | None = None,
) -> str:
    lines = [
        f"  {entry.discipline.name}"
        + (f" ({t('email.confirmation.substitute', lang)})" if entry.is_substitute else "")
        for entry in registration.entries
    ]
    # two teams in one discipline are two lines, never a quantity (design
    # team-disciplines 5.1); the waitlisted marker reuses the substitute
    # marker's shape but is worded distinctly (a team is not a fencer queue)
    at = registration.registered_at.date()
    for team in registration.teams:
        fee = format_money(
            pricing.discipline_fee(tournament, team.discipline, at, "local"),
            tournament.local_currency,
            lang,
        )
        marker = f" ({t('email.confirmation.teamWaitlisted', lang)})" if team.waitlisted else ""
        lines.append(f"  {team.name} — {team.discipline.name}: {fee}{marker}")
    if registration.weapon_rentals:
        lines.append(
            f"  {t('email.confirmation.rentals', lang)}: " + ", ".join(registration.weapon_rentals)
        )
    if registration.afterparty:
        lines.append(f"  {t('email.confirmation.afterparty', lang)}")
    for selection in registration.extra_selections:
        qty_suffix = f" ×{selection.qty}" if selection.qty > 1 else ""
        # the option answer belongs beside its item, labelled as the organizer
        # named it ("size: M"), so the fencer can check what they ordered
        option = ""
        if selection.option_value:
            label = selection.item.option_label or t("email.confirmation.option", lang)
            option = f" ({label}: {selection.option_value})"
        lines.append(f"  {selection.item.name}{qty_suffix}{option}")
    if registration.aftersparring:
        lines.append(f"  {t('email.confirmation.aftersparring', lang)}")
    # the participation condition, and — where it is not met — what the fencer
    # is waiting for (spec registration, Participation condition)
    condition = [e.discipline for e in registration.entries if e.conditional]
    if condition:
        names = ", ".join(discipline.name for discipline in condition)
        lines.append(f"  {t('email.confirmation.condition', lang, disciplines=names)}")
        full = [d.name for d in condition if d.slug in (waits_for or [])]
        if full:
            lines.append(
                f"  {t('email.confirmation.conditionWaits', lang, disciplines=', '.join(full))}"
            )
    return "\n".join(lines)


def _eur_note(tournament: Tournament, lang: str) -> str:
    """The sentence pointing at the second, EUR-denominated QR; empty for a
    tournament that takes only its local currency."""
    if not tournament.shows_eur:
        return ""
    return t("email.confirmation.eur_note", lang)


def _amount_text(
    tournament: Tournament, lang: str, local_amount: int | Decimal, eur_amount: int | Decimal | None
) -> str:
    """A local-currency figure with the stored EUR figure appended when the
    tournament takes EUR — one string so every email body has a single slot.
    Neither figure is ever computed from the other."""
    primary = format_money(local_amount, tournament.local_currency, lang)
    if eur_amount is None:
        return primary
    return f"{primary} ({format_money(eur_amount, 'EUR', lang)})"


def _total_text(tournament: Tournament, registration: Registration) -> str:
    return _amount_text(
        tournament, tournament.language, registration.total_amount, registration.total_eur
    )


def _day(tournament: Tournament, moment: datetime.date | datetime.datetime, lang: str) -> str:
    """A date as the message's language writes it (spec outgoing-mail, Dates in
    messages follow the communication language). An instant — a payment
    window's close — is stated as its day where the tournament is held; the
    boundary itself stays the instant (spec day-boundaries)."""
    if isinstance(moment, datetime.datetime):
        moment = local_date(tournament, moment)
    return format_date(moment, lang)


def _due_text(registration: Registration, lang: str) -> str:
    """The date money is due by, for the mails that state a window's close. The
    window is stored as an instant; the fencer needs the day."""
    if registration.expires_at is None:
        return t("email.promoted.noDeadline", lang)
    return _day(registration.tournament, registration.expires_at, lang)


def _account_text(tournament: Tournament) -> str:
    """The account in the form its payer can use — both forms for a Czech
    account, the IBAN alone otherwise (design accept-czech-account-format
    Decision 2)."""
    if not tournament.bank_account:
        return "?"
    return accounts.display(tournament.bank_account)


def recipient(registration: Registration, fencer: Fencer) -> str | None:
    """Where a message about this registration goes.

    The seat's own contact address where it has one, the account holder's
    otherwise. A substitution that kept the address the seat came with writes
    the first, and from then on the seat is written to rather than the person
    holding it (spec `registration`, "A registration may carry a contact address
    of its own").

    One function because there are fourteen sends and a fifteenth will be added
    without reading this file."""
    return registration.contact_email or fencer.email


def tournament_link(tournament: Tournament) -> str:
    """The tournament's public page, spelled as the frontend's `routes.detail`
    spells it. Carries no key and grants nothing by itself."""
    return f"{settings.public_base_url}/t/{tournament.slug}"


def manage_link(registration: Registration) -> str | None:
    """The guest registration's manage link, or `None` where it is not a guest's
    (spec `guest-registration`, A guest registration is managed through a link).

    The key is carried in the fragment, which the browser never sends to the
    server and never passes on in a referrer."""
    key = managekey.key_for(registration)
    if key is None:
        return None
    return f"{settings.public_base_url}/t/{registration.tournament.slug}/manage#{key}"


def _letter(
    registration: Registration,
    to: str | None,
    subject: str,
    body: str,
    qr: bytes | None = None,
    qr_eur: bytes | None = None,
    qrs: list[tuple[str, bytes]] | None = None,
) -> EmailMessage:
    """Every message about a registration, built in one place so that each
    carries the link to its tournament's page (spec outgoing-mail, Every
    registration message links to its tournament) and, where the registration
    is a guest's, the manage link — whichever message it is and whatever caused
    it. The same reasoning as `recipient`: a fifteenth send will be added
    without reading this file, and it must not be the one without its links."""
    lang = registration.tournament.language
    body += "\n\n" + t("email.tournamentLink", lang, link=tournament_link(registration.tournament))
    link = manage_link(registration)
    if link is not None:
        body += "\n\n" + t("email.manageLink", lang, link=link)
    return build_message(
        to, settings.email_sender, subject, body, qr=qr, qr_eur=qr_eur, named_qrs=qrs
    )


def send_manage_link(mailer: Mailer, tournament: Tournament, registration: Registration) -> None:
    """A guest's manage link sent again, at the organizer's hand (spec
    guest-registration, A guest registration is managed through a link). The
    current key, not a fresh one: the link already mailed stays good, so a
    guest who finds the first mail after all is not left holding a dead one.
    The link itself is the letter's own footer."""
    lang = tournament.language
    fencer = registration.fencer
    body = t(
        "email.manageLinkResent.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
    )
    body += "\n\n" + t("email.manageLinkResent.signature", lang, tournament=tournament.display_name)
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t("email.manageLinkResent.subject", lang, tournament=tournament.display_name),
            body,
        )
    )


def send_signup_verification(mailer: Mailer, pending: PendingSignup, key: str) -> None:
    """The link that finishes a signup (spec `fencer-accounts`, An account exists
    only once its address is verified). In the language the signer chose, since
    there is no tournament whose communication language would apply."""
    lang = pending.language
    link = f"{settings.public_base_url}/verify#{key}"
    mailer.send(
        build_message(
            pending.email,
            settings.email_sender,
            t("email.verifySignup.subject", lang),
            t("email.verifySignup.body", lang, name=pending.display_name, link=link),
        )
    )


def send_password_reset(mailer: Mailer, fencer: Fencer, key: str) -> None:
    """The link that sets a new password (spec `password-reset`). To the
    account's own address, never a registration's `recipient()`: it is the
    account being recovered, not a registration being written about. In the
    account's language, as no tournament's communication language applies."""
    lang = fencer.language
    link = f"{settings.public_base_url}/reset#{key}"
    mailer.send(
        build_message(
            fencer.email,
            settings.email_sender,
            t("email.passwordReset.subject", lang),
            t("email.passwordReset.body", lang, name=fencer.display_name, link=link),
        )
    )


def send_password_changed(mailer: Mailer, fencer: Fencer) -> None:
    """The notice after a password change on the Profile page (spec
    `profile-page`, Password change). Anyone at a browser already signed in
    can make that change; the address is how the owner learns of it. No link:
    the way back is Forgot password on the sign-in screen, which it names."""
    lang = fencer.language
    mailer.send(
        build_message(
            fencer.email,
            settings.email_sender,
            t("email.passwordChanged.subject", lang),
            t("email.passwordChanged.body", lang, name=fencer.display_name),
        )
    )


def _payment_mail_suppressed(
    tournament: Tournament,
    registration: Registration | None = None,
    *,
    despite_dormancy: bool = False,
) -> bool:
    """Whether this payment message is not sent at all. Guarded here, at the one
    place every such message is composed, rather than at each of the several
    callers.

    Two reasons, and the second is per registration.

    With the payments feature off Squire requests no money, so a reminder, an
    expiry notice, a surcharge or a payment-received message has nothing to be
    about (spec payments).

    And **a registration whose clocks are dormant is never written to at all**.
    Those are rows issued from an imported list: people who registered through
    somebody else's form, often a season ago, often having already paid, and to
    whom Squire has never sent anything. The spec names reminders and expiry
    notices, which the scheduler would have sent; this is the same silence on
    the path a person triggers, and it is the one that would actually have
    fired — crediting an issued registration is expressly allowed, so an
    organizer reconciling last season's statement would have mailed the whole
    roster by clicking Confirm forty-three times.

    What is dormant is the passage of time and not the money: such a
    registration is still matched, still linked and still credited. It is only
    The one exception is a statement about money that has just changed under
    the fencer's feet. An organizer's discipline correction that leaves an
    issued registration owing more is told, dormant or not (spec
    `discipline-amendment`, The fencer is told only where the correction costs
    them): what dormancy suspends is the passage of time — the reminders and
    the expiry notice — and the surcharge carries information the fencer cannot
    get any other way and must act on. `despite_dormancy` is how that one
    message says so; nothing else passes it."""
    if not tournament.feature_payments:
        return True
    if registration is not None and _entered_by_hand(registration):
        # no exception reaches a hand entry: the organizer who entered the
        # fencer is the one in contact with them (design manual-entry-registers D3)
        return True
    if despite_dormancy:
        return False
    return registration is not None and registration.clocks_dormant


def dormant_by_origin(registration: Registration) -> bool:
    """A registration Squire never writes to, whatever the tournament's payments
    setting: one issued for a source row, whose fencer registered through
    somebody else's form, and one entered by hand at the console, whose fencer
    is in contact with the organizer who entered them (spec registration, A
    registration entered by hand). Asked by the letters `_payment_mail_suppressed`
    does not guard — the confirmations and the promotion notice, which a
    payments-off tournament still sends."""
    return registration.clocks_dormant


def _entered_by_hand(registration: Registration) -> bool:
    """Dormant by origin and issued for no source row: a hand entry on an
    automatic tournament (design manual-entry-registers D2)."""
    return registration.clocks_dormant and registration.source_row_id is None


def _send_confirmation_without_payment(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration, key: str
) -> None:
    """The confirmation a payments-off tournament sends: the summary and the
    total, and nothing about paying it — no account, no variable symbol, no QR
    code and no expiry date. It confirms the registration rather than
    requesting money; how the event is settled is the organizer's own
    statement, made in the registration instructions."""
    lang = tournament.language
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t(f"{key}.subject", lang, tournament=tournament.display_name),
            t(
                f"{key}.body",
                lang,
                name=fencer.display_name,
                tournament=tournament.display_name,
                summary=_summary_lines(registration, tournament, lang),
                total=_total_text(tournament, registration),
            ),
        )
    )


def send_registration_confirmation(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    *,
    waits_for: list[str] | None = None,
) -> None:
    """`waits_for` names, by slug, the disciplines of an unmet participation
    condition that have no free place, which the summary states."""
    if dormant_by_origin(registration):
        return
    lang = tournament.language
    queued = registration.fully_queued

    if not queued and not tournament.feature_payments:
        _send_confirmation_without_payment(
            mailer, tournament, fencer, registration, "email.confirmationNoPayment"
        )
        return

    if queued:
        subject = t("email.queued.subject", lang, tournament=tournament.display_name)
        summary = _summary_lines(registration, tournament, lang, waits_for)
        if pricing.ensure_claim(registration, tournament) and tournament.bank_account:
            # the tournament lets paying substitutes take free places: the
            # fencer is told what to pay and when it takes a place (spec payments)
            claim, qr, qr_eur = _claim_block(tournament, registration, lang)
            body = t(
                "email.queued.bodyClaim",
                lang,
                name=fencer.display_name,
                tournament=tournament.display_name,
                summary=summary,
                claim=claim,
            )
            mailer.send(
                _letter(
                    registration,
                    recipient(registration, fencer),
                    subject,
                    body,
                    qr=qr,
                    qr_eur=qr_eur,
                )
            )
            return
        body = t(
            "email.queued.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            summary=summary,
        )
        mailer.send(_letter(registration, recipient(registration, fencer), subject, body))
        return

    subject = t("email.confirmation.subject", lang, tournament=tournament.display_name)
    amounts, consequence, qrs = _payment_block(tournament, registration, lang)
    body = t(
        "email.confirmation.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, tournament, lang, waits_for),
        amounts=amounts,
        consequence=consequence,
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body, qrs=qrs))


def payment_message(tournament: Tournament, registration: Registration) -> str:
    return f"VS{registration.vs} {tournament.display_name}"


def payment_spayd(
    tournament: Tournament,
    registration: Registration,
    *,
    local_amount: int | Decimal | None = None,
    eur_amount: int | Decimal | None = None,
) -> tuple[str, str | None]:
    """The local-currency SPAYD string and, for a tournament that also takes
    EUR, a second one denominated in EUR against the same IBAN (design D4).

    The two override amounts are independent — the same VS, but for whatever
    is outstanding in each currency (a surcharge due) rather than each
    currency's full total. Each defaults to that currency's stored total."""
    account = tournament.bank_account
    vs = registration.vs
    if account is None or vs is None:
        # every caller checks the account first and turns a missing one into
        # `no_bank_account`/no QR; a symbol is allocated with the registration
        # wherever Squire collects. Stated here so neither can arrive as a
        # `None` inside a payment string a fencer would scan.
        raise ValueError("a SPAYD string needs both a bank account and a symbol")
    local_due = registration.total_amount if local_amount is None else local_amount
    message = payment_message(tournament, registration)
    primary = spayd.spayd_string(
        account,
        local_due,
        vs,
        message,
        currency=str(tournament.local_currency),
    )
    eur_due = registration.total_eur if eur_amount is None else eur_amount
    if eur_due is None:
        return primary, None
    eur = spayd.spayd_string(
        account,
        eur_due,
        vs,
        message,
        currency="EUR",
    )
    return primary, eur


def payment_qrs(
    tournament: Tournament,
    registration: Registration,
    *,
    local_amount: int | Decimal | None = None,
    eur_amount: int | Decimal | None = None,
) -> tuple[bytes | None, bytes | None]:
    # no QR is produced for a tournament Squire collects nothing for: a code
    # drawn on an account no money is owed into is a demand the tournament is
    # not making (spec payments)
    if not tournament.feature_payments or not tournament.bank_account:
        return None, None
    primary, eur = payment_spayd(
        tournament, registration, local_amount=local_amount, eur_amount=eur_amount
    )
    return spayd.qr_png(primary), (spayd.qr_png(eur) if eur else None)


def _units(cents: int) -> int | Decimal:
    """Cents as the amount a letter states and a QR code encodes; a whole
    amount reads as one."""
    amount = (Decimal(cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount) if amount == amount.to_integral_value() else amount


def _qr_pair(
    tournament: Tournament,
    registration: Registration,
    lang: str,
    stem_key: str,
    local: int | Decimal,
    eur: int | Decimal | None,
) -> list[tuple[str, bytes]]:
    """One amount's codes, local and — where the tournament takes it — EUR,
    each named for what it pays and its currency."""
    qr, qr_eur = payment_qrs(tournament, registration, local_amount=local, eur_amount=eur)
    stem = t(stem_key, lang)
    named = []
    if qr is not None:
        named.append((f"{stem}.png", qr))
    if qr_eur is not None:
        named.append((f"{stem}-eur.png", qr_eur))
    return named


def _payment_block(
    tournament: Tournament, registration: Registration, lang: str
) -> tuple[str, str, list[tuple[str, bytes]]]:
    """What a confirmation, an amendment and a reminder state about paying, by
    payment mode: the amount lines, the consequence paragraph, and the named QR
    codes (spec registration, Confirmation email with QR payment; spec
    payments, Reminders and expiry notices).

    Four cases, and each states only what will actually happen. A deposit
    window still running asks for the deposit and the total, with a pair of
    codes each. A registration already holding credit — the deposit paid, a
    partial payment — is asked for what is outstanding and nothing more, so
    following it never overpays. Reservation mode owes the total by the
    seating deadline, when an unpaid seat goes to the queue rather than
    expiring. Immediate mode owes the total by the window's close, when the
    place is released."""
    mode = tournament.payment_mode
    seating = _day(tournament, setup.seating_deadline_for(tournament), lang)
    window = _due_text(registration, lang) if registration.expires_at else seating
    takes_eur = registration.total_eur is not None
    credited = registration.credited_in("local") > 0 or (
        takes_eur and registration.credited_in("eur") > 0
    )
    outstanding_local = _units(max(registration.outstanding_in("local"), 0))
    outstanding_eur = _units(max(registration.outstanding_in("eur"), 0)) if takes_eur else None

    if mode == PaymentMode.DEPOSIT and registration.expires_at is not None:
        # the deposit still to send: what of it is not yet credited
        deposit_local = _units(
            max((tournament.deposit_amount or 0) * 100 - registration.credited_in("local"), 0)
        )
        deposit_eur = (
            _units(
                max((tournament.deposit_amount_eur or 0) * 100 - registration.credited_in("eur"), 0)
            )
            if takes_eur
            else None
        )
        lines = t(
            "email.due.deposit.lines",
            lang,
            deposit=_amount_text(tournament, lang, deposit_local, deposit_eur),
            total=_amount_text(tournament, lang, outstanding_local, outstanding_eur),
            window=window,
            seating=seating,
        )
        consequence = t("email.due.deposit.consequence", lang, window=window, seating=seating)
        qrs = _qr_pair(
            tournament, registration, lang, "email.due.qrDeposit", deposit_local, deposit_eur
        ) + _qr_pair(
            tournament, registration, lang, "email.due.qrTotal", outstanding_local, outstanding_eur
        )
        return lines, consequence, qrs

    releases = mode == PaymentMode.IMMEDIATE
    due = window if releases else seating
    consequence = t("email.due.releases" if releases else "email.due.queues", lang, due=due)
    if credited:
        lines = t(
            "email.due.balance",
            lang,
            outstanding=_amount_text(tournament, lang, outstanding_local, outstanding_eur),
            due=due,
        )
        qrs = _qr_pair(
            tournament,
            registration,
            lang,
            "email.due.qrBalance",
            outstanding_local,
            outstanding_eur,
        )
        return lines, consequence, qrs
    lines = t("email.due.total", lang, total=_total_text(tournament, registration), due=due)
    qrs = _qr_pair(
        tournament,
        registration,
        lang,
        "email.due.qrTotal",
        registration.total_amount,
        registration.total_eur,
    )
    return lines, consequence, qrs


def send_payment_reminder(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    subject = t("email.reminder.subject", lang, tournament=tournament.display_name)
    amounts, consequence, qrs = _payment_block(tournament, registration, lang)
    body = t(
        "email.reminder.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        amounts=amounts,
        consequence=consequence,
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body, qrs=qrs))


def send_reservation_expired(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    *,
    holding_payment: bool = False,
) -> None:
    """`holding_payment` branches the notice for a reservation that expired
    while carrying a partial payment (design harden-payment-matching
    Decision 3): it states the organizer holds the money and will be in
    contact, and never implies the money is lost or promises a seat."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    if holding_payment:
        subject = t("email.expiredHoldingPayment.subject", lang, tournament=tournament.display_name)
        body = t(
            "email.expiredHoldingPayment.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            vs=registration.vs,
        )
    else:
        subject = t("email.expired.subject", lang, tournament=tournament.display_name)
        body = t(
            "email.expired.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            vs=registration.vs,
        )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body))


def send_payment_received(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    subject = t("email.paid.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.paid.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        total=_total_text(tournament, registration),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body))


def send_partial_payment_received(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    which: Literal["local", "eur"],
) -> None:
    """The registration stays reserved; the fencer is told what is still
    outstanding in the currency this payment credited, rather than being left
    to work the difference out themselves (design harden-payment-matching
    Decision 3)."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    outstanding = Decimal(registration.outstanding_in(which)) / 100
    currency = tournament.local_currency if which == "local" else Currency.EUR
    outstanding = outstanding.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    subject = t("email.partial.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.partial.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        outstanding=format_money(outstanding, currency, lang),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body))


def send_amendment_confirmation(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """Same content as the initial confirmation — the updated summary, the
    recomputed amount, and a QR against the unchanged VS — reissued because a
    reserved amendment leaves `vs` and `expires_at` untouched (Decision 3)."""
    if dormant_by_origin(registration):
        return
    lang = tournament.language
    queued = all(entry.is_substitute for entry in registration.entries) and all(
        team.waitlisted for team in registration.teams
    )

    if not queued and not tournament.feature_payments:
        _send_confirmation_without_payment(
            mailer, tournament, fencer, registration, "email.amendmentNoPayment"
        )
        return

    if queued:
        subject = t("email.amendment.queuedSubject", lang, tournament=tournament.display_name)
        body = t(
            "email.amendment.queuedBody",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            summary=_summary_lines(registration, tournament, lang),
        )
        mailer.send(_letter(registration, recipient(registration, fencer), subject, body))
        return

    subject = t("email.amendment.subject", lang, tournament=tournament.display_name)
    amounts, consequence, qrs = _payment_block(tournament, registration, lang)
    body = t(
        "email.amendment.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, tournament, lang),
        amounts=amounts,
        consequence=consequence,
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body, qrs=qrs))


def send_surcharge_due(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    *,
    despite_dormancy: bool = False,
) -> bool:
    """A registration amended upward: payment instructions for exactly the
    difference in each currency, against the same VS the fencer already paid
    once. The two currencies' outstanding amounts are independent — a price
    change need not move both the same way.

    `despite_dormancy` is the organizer's discipline correction: an issued
    registration that now owes more is told, because the change is theirs to
    act on and nothing else will tell them. Returns whether a message was sent."""
    if _payment_mail_suppressed(tournament, registration, despite_dormancy=despite_dormancy):
        return False
    lang = tournament.language
    outstanding_local = (Decimal(registration.outstanding_cents) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    outstanding_eur = None
    if registration.outstanding_eur_cents is not None:
        outstanding_eur = (Decimal(registration.outstanding_eur_cents) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    subject = t("email.surcharge.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.surcharge.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        amount=_amount_text(tournament, lang, outstanding_local, outstanding_eur),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    qr, qr_eur = payment_qrs(
        tournament, registration, local_amount=outstanding_local, eur_amount=outstanding_eur
    )
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            subject,
            body,
            qr=qr,
            qr_eur=qr_eur,
        )
    )
    return True


def send_promoted(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    discipline_name: str,
) -> None:
    """A queued placement promoted into a seat: the news is that the fencer got
    in, so the mail leads with the discipline whose place opened rather than
    with the bill.

    The amount is what is *now* due — `outstanding_cents` against what has
    already been credited — not the registration's total. A registration that
    was fully queued owes its whole total and the two coincide; one that had
    already paid for a seat beside this queued placement owes only the
    difference, and must not be sent a demand reading as though nothing had
    been paid (spec: seating-queue, "Organizer promotion from the queue").

    With payments off no window opens and nothing is due, so the same news is
    sent with the registration's total stated as information — the shape
    `send_surcharge_due` has no room for.

    A registration dormant by origin is sent neither: its fencer was never
    written to by Squire and a promotion does not start (spec registration, A
    registration entered by hand; imported-registrations)."""
    if dormant_by_origin(registration):
        return
    lang = tournament.language
    if not tournament.feature_payments:
        mailer.send(
            _letter(
                registration,
                recipient(registration, fencer),
                t("email.promotedNoPayment.subject", lang, tournament=tournament.display_name),
                t(
                    "email.promotedNoPayment.body",
                    lang,
                    name=fencer.display_name,
                    tournament=tournament.display_name,
                    discipline=discipline_name,
                    total=_total_text(tournament, registration),
                ),
            )
        )
        return

    if registration.settled:
        # money the fencer sent while queued was credited by the promotion
        # itself and covers the place, so the letter confirms it rather than
        # asking for anything (spec seating-queue)
        mailer.send(
            _letter(
                registration,
                recipient(registration, fencer),
                t("email.promotedPaid.subject", lang, tournament=tournament.display_name),
                t(
                    "email.promotedPaid.body",
                    lang,
                    name=fencer.display_name,
                    tournament=tournament.display_name,
                    discipline=discipline_name,
                ),
            )
        )
        return

    outstanding_local = (Decimal(registration.outstanding_cents) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    outstanding_eur = None
    if registration.outstanding_eur_cents is not None:
        outstanding_eur = (Decimal(registration.outstanding_eur_cents) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    body = t(
        "email.promoted.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        discipline=discipline_name,
        amount=_amount_text(tournament, lang, outstanding_local, outstanding_eur),
        due=_due_text(registration, lang),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    qr, qr_eur = payment_qrs(
        tournament, registration, local_amount=outstanding_local, eur_amount=outstanding_eur
    )
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t("email.promoted.subject", lang, tournament=tournament.display_name),
            body,
            qr=qr,
            qr_eur=qr_eur,
        )
    )


def send_team_promoted(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration, team
) -> None:
    """A waitlisted team admitted into a free slot, told to its entering fencer:
    the promotion notice, naming the team and its discipline and stating what
    is now due (spec seating-queue, The team waitlist in the Queue phase)."""
    label = t(
        "email.promoted.team",
        tournament.language,
        team=team.name,
        discipline=team.discipline.name,
    )
    send_promoted(mailer, tournament, fencer, registration, label)


def send_reservation_reinstated(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    which: Literal["local", "eur"],
    received_cents: int,
) -> None:
    """A payment that reinstated an expired reservation, within grace or by the
    organizer's action: one message combining the reinstatement and the
    payment (spec payments, Payments arriving after expiry).

    Two variants, decided by the money rather than by who reinstated. Where
    the payment settles the registration it is confirmed. Where it falls short
    the fencer is told what arrived and what is still due, by when, with codes
    for the remainder — and is not told their place is confirmed,
    which it is not. Both state the amount received, never the total."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    currency = tournament.local_currency if which == "local" else Currency.EUR
    received = format_money(_units(received_cents), currency, lang)
    if registration.settled:
        subject = t("email.reinstated.subject", lang, tournament=tournament.display_name)
        body = t(
            "email.reinstated.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            total=received,
            vs=registration.vs,
        )
        mailer.send(_letter(registration, recipient(registration, fencer), subject, body))
        return

    # what is still due, by when and with which consequence, is the same block
    # the confirmation and the reminder carry — so a reinstated deposit
    # registration is told about its deposit and the seating deadline too
    amounts, consequence, qrs = _payment_block(tournament, registration, lang)
    subject = t("email.reinstatedPartial.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.reinstatedPartial.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        received=received,
        amounts=amounts,
        consequence=consequence,
        account=_account_text(tournament),
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body, qrs=qrs))


def send_payment_after_expiry(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """A payment that could not be reinstated automatically — outside grace,
    or the seat is gone. States plainly that it arrived and that the organizer
    will follow up; it must not promise a seat that may no longer exist."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    subject = t("email.afterExpiry.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.afterExpiry.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        vs=registration.vs,
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body))


def _credit_text(tournament: Tournament, registration: Registration, lang: str) -> str | None:
    """What this registration holds in credit, in each lane that holds any, or
    None where it holds nothing. The two lanes are alternative prices, so each
    is stated in its own currency and never summed."""
    parts = []
    for which, currency in (("local", tournament.local_currency), ("eur", Currency.EUR)):
        cents = registration.credited_in(which)
        if cents > 0:
            # a whole amount reads as one, as the fencer paid it
            amount = cents // 100 if cents % 100 == 0 else Decimal(cents) / 100
            parts.append(format_money(amount, currency, lang))
    return " + ".join(parts) if parts else None


def send_demoted(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    moved: list[tuple[str, int]],
    moved_teams: list[tuple[str, str, int]],
) -> bool:
    """A registration moved to the substitute queue for non-payment (spec
    registration, Demotion is announced): the disciplines — `(name, queue
    position)` — and teams — `(team, discipline, waitlist position)` — it was
    moved out of a seat in, that nothing is owed while it waits and nothing
    should be sent, and that a promotion opens a new window.

    Credit it holds — a deposit, a partial payment — is stated as staying
    recorded and counting on promotion. Its refund is never promised: whether
    the money comes back is the organizer's decision, not this letter's.

    The positions are read by the caller after the demotion is committed, so
    they are the ones the fencer then sees in the app. Returns whether a
    message was sent, so the caller can record the notice beside the demotion."""
    if _payment_mail_suppressed(tournament, registration):
        return False
    lang = tournament.language
    lines = [
        "  " + t("email.demoted.entry", lang, discipline=name, position=position)
        for name, position in moved
    ] + [
        "  " + t("email.demoted.team", lang, team=team, discipline=name, position=position)
        for team, name, position in moved_teams
    ]
    held = _credit_text(tournament, registration, lang)
    credit = t("email.demoted.credit", lang, amount=held) if held is not None else ""
    qr = qr_eur = None
    if pricing.ensure_claim(registration, tournament) and tournament.bank_account:
        # where paying substitutes take free places the notice tells the fencer
        # what to pay instead of asking them not to (spec registration)
        claim, qr, qr_eur = _claim_block(tournament, registration, lang)
        body = t(
            "email.demoted.bodyClaim",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            vs=registration.vs,
            moved="\n".join(lines),
            credit=credit,
            claim=claim,
        )
    else:
        body = t(
            "email.demoted.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            vs=registration.vs,
            moved="\n".join(lines),
            credit=credit,
        )
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t("email.demoted.subject", lang, tournament=tournament.display_name),
            body,
            qr=qr,
            qr_eur=qr_eur,
        )
    )
    return True


def send_payment_while_queued(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    *,
    reason: str = "registration_queued",
) -> None:
    """A payment on a registration sitting entirely in the queue, held rather
    than credited (spec payments, Payments arriving on a queued registration):
    it arrived, the fencer holds no place, and the organizer will be in contact.
    It promises no place and does not imply the money is lost — the organizer
    resolves it by promoting the fencer or by marking it for refund.

    Where paying substitutes take free places the letter says why it was held:
    it matched the claim and a discipline is full, so it will take the places
    as soon as they free — or its amount is not the claim, which the organizer
    resolves (spec payments)."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    body_key = {
        "queued_no_place": "email.paymentWhileQueued.bodyNoPlace",
        "queued_amount_mismatch": "email.paymentWhileQueued.bodyAmountMismatch",
    }.get(reason, "email.paymentWhileQueued.body")
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t("email.paymentWhileQueued.subject", lang, tournament=tournament.display_name),
            t(
                body_key,
                lang,
                name=fencer.display_name,
                tournament=tournament.display_name,
                vs=registration.vs,
            ),
        )
    )


def send_seated_by_payment(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    disciplines: str,
    which: Literal["local", "eur"],
    received_cents: int,
) -> None:
    """A waiting fencer's payment of their claim took the places they waited
    for: they have a place, and the payment was received (spec seating-queue,
    A paying substitute takes free places). The amount stated is the payment,
    not the registration's total, which is a different figure once the claim
    and the total diverge."""
    if _payment_mail_suppressed(tournament, registration):
        return
    lang = tournament.language
    mailer.send(
        _letter(
            registration,
            recipient(registration, fencer),
            t("email.seatedByPayment.subject", lang, tournament=tournament.display_name),
            t(
                "email.seatedByPayment.body",
                lang,
                name=fencer.display_name,
                tournament=tournament.display_name,
                discipline=disciplines,
                total=format_money(
                    _units(received_cents),
                    tournament.local_currency if which == "local" else Currency.EUR,
                    lang,
                ),
                vs=registration.vs,
            ),
        )
    )


def claim_due(registration: Registration) -> tuple[Decimal, Decimal | None]:
    """What is still to pay of the registration's stored claim, per lane, as
    the amounts a letter and its QR codes state (design paying-substitutes D1)."""
    local = Decimal(pricing.claim_outstanding_cents(registration, "local") or 0) / 100
    eur_cents = pricing.claim_outstanding_cents(registration, "eur")
    eur = None if eur_cents is None else Decimal(eur_cents) / 100
    return (
        local.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        None if eur is None else eur.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )


def _claim_block(
    tournament: Tournament, registration: Registration, lang: str
) -> tuple[str, bytes | None, bytes | None]:
    """The instructions for a waiting registration's claim, as a paragraph and
    its QR codes: the amount, the account, the symbol, and when the payment
    takes a place."""
    local, eur = claim_due(registration)

    def stated(amount: Decimal) -> int | Decimal:
        # a whole amount reads as one
        return int(amount) if amount == amount.to_integral_value() else amount

    text = t(
        "email.claim.block",
        lang,
        amount=_amount_text(tournament, lang, stated(local), None if eur is None else stated(eur)),
        account=_account_text(tournament),
        vs=registration.vs,
    )
    qr, qr_eur = payment_qrs(tournament, registration, local_amount=local, eur_amount=eur)
    return text, qr, qr_eur


def send_composition_reminder(
    mailer: Mailer,
    tournament: Tournament,
    fencer: Fencer,
    registration: Registration,
    teams: list,
    deadline: datetime.date,
) -> None:
    """Reminds the entering fencer, once per team, that a roster is still
    below its discipline's minimum ahead of the composition deadline (spec:
    "Composition reminder to the entering fencer"). `teams` are this fencer's
    own short teams and `registration` the one they belong to, which decides
    where the message goes; the deadline is stated once since a tournament carries a
    single one (design D7), and the caller passes the value it already narrowed
    to reach the reminder window at all. Sends nothing and touches no pricing, VS, or
    capacity path — scheduler.process_composition_reminders stamps
    `composition_reminded_at` per team so a later tick does not resend it."""
    lang = tournament.language
    lines = [
        f"  {team.name} — {team.discipline.name}: "
        + t(
            "email.compositionReminder.count",
            lang,
            have=len(team.members),
            min=team.discipline.team_min,
        )
        for team in teams
    ]
    subject = t("email.compositionReminder.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.compositionReminder.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        teams="\n".join(lines),
        deadline=_day(tournament, deadline, lang),
    )
    mailer.send(_letter(registration, recipient(registration, fencer), subject, body))


def send_substitution(mailer: Mailer, tournament: Tournament, prepared: Prepared) -> None:
    """A seat that has changed hands, told to both people it concerns.

    The substitute learns what they have inherited and what, if anything, is
    still owed on it; the fencer who has gone learns who took their place. Where
    the seat's address was kept, the two are one address and one message is
    sent — the arrival, which is the one that says something the reader has to
    act on (spec `fencer-substitution`, "Both parties are told, once each").

    The amount is what is *now* outstanding and not the registration's total, as
    a promotion's is: a seat already paid for is inherited paid for, and a
    demand reading as though nothing had been paid would send its new holder to
    pay it twice.
    """
    registration = prepared.registration
    if registration is None or _entered_by_hand(registration):
        # a hand-entered seat is sent nothing of any kind; the organizer who
        # entered it is the one in contact (spec registration)
        return
    lang = tournament.language
    substitute, previous = prepared.substitute, prepared.previous
    arrival_to = recipient(registration, substitute)

    if arrival_to:
        outstanding_local = (Decimal(registration.outstanding_cents) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        outstanding_eur = None
        if registration.outstanding_eur_cents is not None:
            outstanding_eur = (Decimal(registration.outstanding_eur_cents) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        owing = tournament.feature_payments and outstanding_local > 0
        key = "email.substituteArrived" if owing else "email.substituteArrivedSettled"
        fields = {
            "name": substitute.display_name,
            "previous": previous.name,
            "tournament": tournament.display_name,
            "summary": _summary_lines(registration, tournament, lang),
        }
        if owing:
            fields |= {
                "amount": _amount_text(tournament, lang, outstanding_local, outstanding_eur),
                "due": _due_text(registration, lang),
                "account": _account_text(tournament),
                "vs": registration.vs,
            }
        qr, qr_eur = (
            payment_qrs(
                tournament,
                registration,
                local_amount=outstanding_local,
                eur_amount=outstanding_eur,
            )
            if owing
            else (None, None)
        )
        mailer.send(
            _letter(
                registration,
                arrival_to,
                t(f"{key}.subject", lang, tournament=tournament.display_name),
                t(f"{key}.body", lang, **fields),
                qr=qr,
                qr_eur=qr_eur,
            )
        )

    # One address, one message: the kept address is the substitute's contact
    # too, and a second letter to it would tell the same person their place had
    # been taken by themselves.
    if not previous.email or previous.email == arrival_to:
        return
    mailer.send(
        build_message(
            previous.email,
            settings.email_sender,
            t("email.substituteDeparted.subject", lang, tournament=tournament.display_name),
            # not through `_letter`: the seat's manage link now belongs to the
            # substitute, so the departing holder gets the tournament link alone
            t(
                "email.substituteDeparted.body",
                lang,
                name=previous.name,
                substitute=substitute.display_name,
                tournament=tournament.display_name,
            )
            + "\n\n"
            + t("email.tournamentLink", lang, link=tournament_link(tournament)),
        )
    )


def send_cancelled_by_organizer(
    mailer: Mailer, tournament: Tournament, registration: Registration, note: str | None
) -> None:
    """A registration the organizer cancelled, told to the person who held it
    (spec registration, An organizer may cancel a registration).

    Sent under the rule every organizer action on a seat follows, the one
    `send_substitution` keeps: a seat the organizer entered by hand is sent
    nothing, the organizer being the one in contact, and a seat with no address
    has nowhere to be sent. Money already paid is not promised back: the
    refund is the organizer's to settle, and the mail says so and no more."""
    if _entered_by_hand(registration):
        return
    to = recipient(registration, registration.fencer)
    if not to:
        return
    lang = tournament.language
    # any money in either lane, a deposit included: whatever arrived is the
    # organizer's to return or keep
    paid = registration.credited_in("local") > 0 or registration.credited_in("eur") > 0
    body = t(
        "email.cancelledByOrganizer.body",
        lang,
        name=registration.fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, tournament, lang),
    )
    if note:
        body += "\n\n" + t("email.cancelledByOrganizer.note", lang, note=note)
    if paid:
        body += "\n\n" + t("email.cancelledByOrganizer.refund", lang)
    body += "\n\n" + t(
        "email.cancelledByOrganizer.signature", lang, tournament=tournament.display_name
    )
    subject = t("email.cancelledByOrganizer.subject", lang, tournament=tournament.display_name)
    mailer.send(_letter(registration, to, subject, body))
