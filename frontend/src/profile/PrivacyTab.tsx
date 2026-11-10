import { useTranslation } from "react-i18next";

import type { Account } from "../api";
import { privacy } from "../routes";
import AccountDeletion from "./AccountDeletion";
import DataSection from "./DataSection";

/** Everything about the account's personal data in one place (spec
 *  `profile-page`, The Profile page has a Privacy tab): who is responsible and
 *  how to reach them, the account's own data to download, the organizer terms
 *  it accepted, and deleting it. */
export default function PrivacyTab({
  account,
  onUpdated,
}: {
  account: Account;
  onUpdated: (account: Account) => void;
}) {
  const { t } = useTranslation();
  const terms = t("privacy.terms.paragraphs", { returnObjects: true }) as string[];
  const acceptedAt = account.organizer_terms_accepted_at;

  return (
    <>
      <section className="rail-card">
        <h2>{t("profile.privacy.title")}</h2>
        <p>{t("profile.privacy.summary")}</p>
        <p>
          <a href={privacy()} target="_blank" rel="noreferrer">
            {t("profile.privacy.readAll")}
          </a>
        </p>
      </section>
      <DataSection />
      {(acceptedAt !== null || account.organizer_terms_due) && (
        <section className="rail-card">
          <h2>{t("privacy.terms.title")}</h2>
          <p className="rail-hint">
            {acceptedAt !== null
              ? t("profile.privacy.termsAccepted", {
                  version: account.organizer_terms_version ?? "",
                  date: new Date(acceptedAt).toLocaleDateString(account.language),
                })
              : t("profile.privacy.termsDue")}
          </p>
          <details>
            <summary>{t("profile.privacy.termsRead")}</summary>
            {terms.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </details>
        </section>
      )}
      <section className="rail-card">
        <h2>{t("profile.deletion.title")}</h2>
        <AccountDeletion account={account} onUpdated={onUpdated} />
      </section>
    </>
  );
}
