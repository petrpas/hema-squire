import { useTranslation } from "react-i18next";

import type { Account } from "../api";

export default function HRBoundSection({ account }: { account: Account }) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{t("profile.hr.title")}</h2>
      <div className="param-fields">
        <div className="param-field">
          <span>{t("admin.accounts.hrId")}</span>
          {/* the identifier is the way to the profile, as in the rosters */}
          <strong>
            <a
              className="external-link"
              href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
              target="_blank"
              rel="noreferrer"
            >
              {account.hr_id}
            </a>
          </strong>
        </div>
        <div className="param-field">
          <span>{t("column.name")}</span>
          <strong>{account.display_name}</strong>
        </div>
        <div className="param-field">
          <span>{t("column.club")}</span>
          <strong>{account.club ?? "—"}</strong>
        </div>
        <div className="param-field">
          <span>{t("column.nationality")}</span>
          <strong>{account.nationality ?? "—"}</strong>
        </div>
      </div>
    </section>
  );
}
