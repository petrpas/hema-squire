import { useTranslation } from "react-i18next";

/** What a manage link whose key is not accepted shows in place of the
 *  registration: a static statement, never an error and never the not-found
 *  screen, since the tournament exists (spec `guest-registration`, The manage
 *  screen). It does not say which of the reasons applies; the server does not
 *  say either. */
export default function ManageLinkDead() {
  const { t } = useTranslation();
  return (
    <section className="rail-card dashed manage-link-dead">
      <p className="rail-hint">{t("guest.linkDead")}</p>
    </section>
  );
}
