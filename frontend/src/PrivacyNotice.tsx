import { useTranslation } from "react-i18next";

import { privacy } from "./routes";

/** The line beside a form that collects personal data, leading to the privacy
 *  notice (spec `privacy`, Collection is accompanied by a notice). It informs
 *  and asks for nothing: the processing does not rest on consent, so there is
 *  no tick. The notice opens in a new tab, so reading it never abandons a
 *  form half filled in — a plain anchor, since a new tab is a fresh page load
 *  and the forms render outside the router in places. */
export default function PrivacyNotice() {
  const { t } = useTranslation();
  return (
    <p className="rail-hint privacy-notice">
      {t("privacy.notice")}{" "}
      <a href={privacy()} target="_blank" rel="noreferrer">
        {t("privacy.noticeLink")}
      </a>
      .
    </p>
  );
}
