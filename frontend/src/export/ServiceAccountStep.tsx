import { useTranslation } from "react-i18next";

import CopyButton from "../CopyButton";

/** The second step of the destination procedure: the address the organizer has
 *  to share their spreadsheet with.
 *
 *  This is the step the whole dialog exists for. The export writes as a service
 *  account, which is an identity of its own: the organizer's own access to the
 *  document grants it nothing, and a document merely visible to it is not one
 *  it can write. Without the address stated, that share is unguessable — and
 *  without it, every export fails on a permission error naming an address the
 *  organizer has never seen.
 *
 *  Where the server holds no credentials there is no address to state, and the
 *  step says so rather than showing an empty value: the link can still be
 *  recorded, it simply will not be written to until the deployment is
 *  configured. */
export default function ServiceAccountStep({ account }: { account: string | null }) {
  const { t } = useTranslation();

  if (account === null) {
    return (
      <li>
        <p>{t("export.wizard.notConfigured")}</p>
      </li>
    );
  }

  return (
    <li>
      <p>{t("export.wizard.share")}</p>
      <div className="slip-value-row">
        {/* Long, and nobody reads it — it is copied. Set smaller so it stays
            one line beside its copy control rather than dominating the step it
            belongs to. */}
        <strong className="data-value wizard-account">{account}</strong>
        <CopyButton
          value={account}
          label={t("export.wizard.copyAccount")}
          done={t("common.copied")}
        />
      </div>
    </li>
  );
}
