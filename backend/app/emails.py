"""Composition of fencer-facing emails, localized to the tournament's
communication language."""

from app import pricing, spayd
from app.config import settings
from app.i18n import format_money, t
from app.mail import Mailer, build_message
from app.models import Fencer, Registration, Tournament


def _summary_lines(registration: Registration, lang: str) -> str:
    lines = [
        f"  {entry.discipline.code} — {entry.discipline.name}"
        + (f" ({t('email.confirmation.substitute', lang)})" if entry.is_substitute else "")
        for entry in registration.entries
    ]
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
    tournament that takes only its primary currency."""
    if not tournament.shows_eur:
        return ""
    return t("email.confirmation.eur_note", lang)


def _total_text(tournament: Tournament, registration: Registration) -> str:
    """The amount due, with the EUR equivalent appended when the tournament
    takes EUR — one string so every email body has a single {total} slot."""
    lang = tournament.language
    primary = format_money(registration.total_amount, tournament.primary_currency, lang)
    eur = pricing.to_eur(registration.total_amount, tournament)
    if eur is None:
        return primary
    return f"{primary} ({format_money(eur, 'EUR', lang)})"


def send_registration_confirmation(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    lang = tournament.language
    queued = all(entry.is_substitute for entry in registration.entries)

    if queued:
        subject = t("email.queued.subject", lang, tournament=tournament.display_name)
        body = t(
            "email.queued.body",
            lang,
            name=fencer.display_name,
            tournament=tournament.display_name,
            summary=_summary_lines(registration, lang),
        )
        mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
        return

    subject = t("email.confirmation.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.confirmation.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        summary=_summary_lines(registration, lang),
        total=_total_text(tournament, registration),
        eur_note=_eur_note(tournament, lang),
        account=tournament.bank_account or "?",
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


def payment_spayd(tournament: Tournament, registration: Registration) -> tuple[str, str | None]:
    """The primary SPAYD string and, for a tournament that also takes EUR, a
    second one denominated in EUR against the same IBAN (design D4)."""
    message = payment_message(tournament, registration)
    primary = spayd.spayd_string(
        tournament.bank_account,
        registration.total_amount,
        registration.vs,
        message,
        currency=str(tournament.primary_currency),
    )
    eur_amount = pricing.to_eur(registration.total_amount, tournament)
    if eur_amount is None:
        return primary, None
    eur = spayd.spayd_string(
        tournament.bank_account,
        eur_amount,
        registration.vs,
        message,
        currency="EUR",
    )
    return primary, eur


def payment_qrs(
    tournament: Tournament, registration: Registration
) -> tuple[bytes | None, bytes | None]:
    if not tournament.bank_account:
        return None, None
    primary, eur = payment_spayd(tournament, registration)
    return spayd.qr_png(primary), (spayd.qr_png(eur) if eur else None)


def send_payment_reminder(
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    lang = tournament.language
    subject = t("email.reminder.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.reminder.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        total=_total_text(tournament, registration),
        eur_note=_eur_note(tournament, lang),
        account=tournament.bank_account or "?",
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
    mailer: Mailer, tournament: Tournament, fencer: Fencer, registration: Registration
) -> None:
    lang = tournament.language
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
    lang = tournament.language
    subject = t("email.paid.subject", lang, tournament=tournament.display_name)
    body = t(
        "email.paid.body",
        lang,
        name=fencer.display_name,
        tournament=tournament.display_name,
        total=format_money(registration.total_amount, tournament.primary_currency, lang),
        vs=registration.vs,
    )
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
