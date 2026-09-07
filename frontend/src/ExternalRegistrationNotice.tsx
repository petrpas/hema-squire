import { useTranslation } from "react-i18next";

import type { TournamentDetail } from "./api";

/** Where a tournament's registration is held, on a page that would otherwise
 *  offer a registration form.
 *
 *  States that registration is held elsewhere — never that it is closed, not
 *  yet open, or over. No window ever existed on this tournament, and each of
 *  those would be a false account of why the fencer cannot enter here (spec
 *  external-registration).
 *
 *  Where no address is recorded the statement stands alone, with no action:
 *  an action that leads nowhere is worse than none. A published tournament
 *  cannot be in that state — the address is mandatory to publish one — but a
 *  draft its organizer is previewing can. */
export default function ExternalRegistrationNotice({ detail }: { detail: TournamentDetail }) {
  const { t } = useTranslation();
  const url = detail.external_registration_url;
  return (
    <section className="rail-card dashed">
      <p>{t("detail.registrationElsewhere")}</p>
      {url && (
        <p>
          <a className="external-link" href={url} target="_blank" rel="noreferrer noopener">
            {t("detail.registrationElsewhereAction")}
          </a>
        </p>
      )}
    </section>
  );
}
