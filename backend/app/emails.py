"""Composition of fencer-facing emails, localized to the tournament's
communication language."""

from app import spayd
from app.config import settings
from app.i18n import t
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
        lines.append(f"  {selection.item.name}{qty_suffix}")
    if registration.aftersparring:
        lines.append(f"  {t('email.confirmation.aftersparring', lang)}")
    return "\n".join(lines)


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
        total=registration.total_amount,
        account=tournament.bank_account or "?",
        vs=registration.vs,
        expires=registration.expires_at.date().isoformat() if registration.expires_at else "-",
    )
    qr = payment_qr(tournament, registration)
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body, qr=qr))


def payment_qr(tournament: Tournament, registration: Registration) -> bytes | None:
    if not tournament.bank_account:
        return None
    payment_message = f"VS{registration.vs} {tournament.display_name}"
    return spayd.qr_png(
        spayd.spayd_string(
            tournament.bank_account,
            registration.total_amount,
            registration.vs,
            payment_message,
        )
    )


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
        total=registration.total_amount,
        account=tournament.bank_account or "?",
        vs=registration.vs,
        expires=registration.expires_at.date().isoformat() if registration.expires_at else "-",
    )
    qr = payment_qr(tournament, registration)
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body, qr=qr))


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
        total=registration.total_amount,
        vs=registration.vs,
    )
    mailer.send(build_message(fencer.email, settings.email_sender, subject, body))
