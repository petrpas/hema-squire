"""Composition of fencer-facing emails, localized to the tournament's
communication language."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app import accounts, pricing, spayd
from app.config import settings
from app.i18n import format_money, t
from app.mail import Mailer, build_message
from app.models import Currency, Fencer, Registration, Tournament


def _summary_lines(registration: Registration, tournament: Tournament, lang: str) -> str:
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
        marker = (
            f" ({t('email.confirmation.teamWaitlisted', lang)})" if team.waitlisted else ""
        )
        lines.append(f"  {team.name} — {team.discipline.name}: {fee}{marker}")
    if registration.weapon_rentals:
        lines.append(
            f"  {t('email.confirmation.rentals', lang)}: "
            + ", ".join(registration.weapon_rentals)
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


def _due_text(registration: Registration, lang: str) -> str:
    """The date money is due by, for the one mail that states a deadline. The
    window is stored as an instant; the fencer needs the day."""
    if registration.expires_at is None:
        return t("email.promoted.noDeadline", lang)
    return registration.expires_at.strftime("%d.%m.%Y")


def _account_text(tournament: Tournament) -> str:
    """The account in the form its payer can use — both forms for a Czech
    account, the IBAN alone otherwise (design accept-czech-account-format
    Decision 2)."""
    if not tournament.bank_account:
        return "?"
    return accounts.display(tournament.bank_account)


def _payment_mail_suppressed(tournament: Tournament) -> bool:
    """Whether this tournament's payment mail is not sent at all. With the
    payments feature off Squire requests no money, so a reminder, an expiry
    notice, a surcharge or a payment-received message has nothing to be about
    (design tournament-modes D5). Guarded here, at the one place every such
    message is composed, rather than at each of the several callers."""
    return not tournament.feature_payments


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
        build_message(
            fencer.email,
            settings.email_sender,
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
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    lang = tournament.language
    queued = registration.fully_queued

    if not queued and not tournament.feature_payments:
        _send_confirmation_without_payment(
            mailer, tournament, fencer, registration, "email.confirmationNoPayment"
        )
        return

    if queued:
        subject = t("email.queued.subject", lang, tournament=tournament.display_name)
        body = t(
            "email.queued.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            summary=_summary_lines(registration, tournament, lang),
        )
        mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
        return

    subject = t("email.confirmation.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.confirmation.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, tournament, lang),
        total=_total_text(tournament, registration),
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
        expires=registration.expires_at.date().isoformat() if registration.expires_at else "-",
    )
    qr, qr_eur = payment_qrs(tournament, registration)
    mailer.send(
        build_message(
            fencer.email, settings.email_sender, subject, body, qr=qr, qr_eur=qr_eur
        )
    )


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
    local_due = registration.total_amount if local_amount is None else local_amount
    message = payment_message(tournament, registration)
    primary = spayd.spayd_string(
        tournament.bank_account,
        local_due,
        registration.vs,
        message,
        currency=str(tournament.local_currency),
    )
    eur_due = registration.total_eur if eur_amount is None else eur_amount
    if eur_due is None:
        return primary, None
    eur = spayd.spayd_string(
        tournament.bank_account,
        eur_due,
        registration.vs,
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
    # not making (design tournament-modes D5)
    if not tournament.feature_payments or not tournament.bank_account:
        return None, None
    primary, eur = payment_spayd(
        tournament, registration, local_amount=local_amount, eur_amount=eur_amount
    )
    return spayd.qr_png(primary), (spayd.qr_png(eur) if eur else None)


def send_payment_reminder(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    if _payment_mail_suppressed(tournament):
        return
    lang = tournament.language
    subject = t("email.reminder.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.reminder.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        total=_total_text(tournament, registration),
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
        expires=registration.expires_at.date().isoformat() if registration.expires_at else "-",
    )
    qr, qr_eur = payment_qrs(tournament, registration)
    mailer.send(
        build_message(
            fencer.email, settings.email_sender, subject, body, qr=qr, qr_eur=qr_eur
        )
    )


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
    if _payment_mail_suppressed(tournament):
        return
    lang = tournament.language
    if holding_payment:
        subject = t(
            "email.expiredHoldingPayment.subject", lang, tournament=tournament.display_name
        )
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
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))


def send_payment_received(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    if _payment_mail_suppressed(tournament):
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
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))


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
    if _payment_mail_suppressed(tournament):
        return
    lang = tournament.language
    if which == "local":
        outstanding = Decimal(registration.outstanding_cents) / 100
        currency = tournament.local_currency
    else:
        outstanding = Decimal(registration.outstanding_eur_cents) / 100
        currency = Currency.EUR
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
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))


def send_amendment_confirmation(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """Same content as the initial confirmation — the updated summary, the
    recomputed amount, and a QR against the unchanged VS — reissued because a
    reserved amendment leaves `vs` and `expires_at` untouched (Decision 3)."""
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
        mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
        return

    subject = t("email.amendment.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.amendment.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, tournament, lang),
        total=_total_text(tournament, registration),
        eur_note=_eur_note(tournament, lang),
        account=_account_text(tournament),
        vs=registration.vs,
        expires=registration.expires_at.date().isoformat() if registration.expires_at else "-",
    )
    qr, qr_eur = payment_qrs(tournament, registration)
    mailer.send(
        build_message(
            fencer.email, settings.email_sender, subject, body, qr=qr, qr_eur=qr_eur
        )
    )


def send_surcharge_due(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """A paid registration amended upward: payment instructions for exactly
    the difference in each currency, against the same VS the fencer already
    paid once. The two currencies' outstanding amounts are independent —
    a price change need not move both the same way."""
    if _payment_mail_suppressed(tournament):
        return
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
        build_message(
            fencer.email, settings.email_sender, subject, body, qr=qr, qr_eur=qr_eur
        )
    )


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
    `send_surcharge_due` has no room for."""
    lang = tournament.language
    if not tournament.feature_payments:
        mailer.send(
            build_message(
                fencer.email,
                settings.email_sender,
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
        build_message(
            fencer.email,
            settings.email_sender,
            t("email.promoted.subject", lang, tournament=tournament.display_name),
            body,
            qr=qr,
            qr_eur=qr_eur,
        )
    )


def send_reservation_reinstated(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """A payment accepted within (or, by organizer action, outside) the expiry
    grace period: one message combining the reinstatement and the payment,
    consistent with the registration already showing as paid by the time this
    is sent (matching.match_new_transactions, routers/payments.reinstate)."""
    if _payment_mail_suppressed(tournament):
        return
    lang = tournament.language
    subject = t("email.reinstated.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.reinstated.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        total=_total_text(tournament, registration),
        vs=registration.vs,
    )
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))


def send_payment_after_expiry(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    """A payment that could not be reinstated automatically — outside grace,
    or the seat is gone. States plainly that it arrived and that the organizer
    will follow up; it must not promise a seat that may no longer exist."""
    if _payment_mail_suppressed(tournament):
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
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))


def send_composition_reminder(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, teams: list
) -> None:
    """Reminds the entering fencer, once per team, that a roster is still
    below its discipline's minimum ahead of the composition deadline (spec:
    "Composition reminder to the entering fencer"). `teams` are this fencer's
    own short teams; the deadline is stated once since a tournament carries a
    single one (design D7). Sends nothing and touches no pricing, VS, or
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
        deadline=tournament.team_composition_deadline.isoformat(),
    )
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
