import { useTranslation } from "react-i18next";

import type { Account } from "../api";
import { privacy } from "../routes";
import AccountDeletion from "./AccountDeletion";
import DataSection from "./DataSection";
import OrganizerTermsButton from "./OrganizerTermsButton";

/** Everything about the account's personal data in one place (spec
 *  `profile-page`, The Profile page has a Privacy tab): who is responsible and
 *  how to reach them, the account's own data to download, deleting it, and
 *  below the rest the organizer terms it accepted. */
export default function PrivacyTab({
  account,
  onUpdated,
}: {
  account: Account;
  onUpdated: (account: Account) => void;
}) {
  const { t } = useTranslation();

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
      <section className="rail-card">
        <h2>{t("profile.deletion.title")}</h2>
        <AccountDeletion account={account} onUpdated={onUpdated} />
      </section>
      <OrganizerTermsButton account={account} />
    </>
  );
}
