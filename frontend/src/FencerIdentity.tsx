import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { profile } from "./routes";
import { type Account } from "./api";

/** Who the fencer is: their display name over their hemaratings identity.
 *
 *  Rendered in two places — the top bar at desktop widths, and inside the
 *  account menu below 768px, where the bar has no room for it. One component
 *  rather than two copies, so the HRID link and the unbound fallback cannot
 *  come to differ between the two.
 *
 *  Which of the two is visible is settled in CSS, not here: branching on a
 *  media query in JavaScript would re-render the bar on every resize and
 *  would need the width resolved before first paint to avoid a flash. */
export default function FencerIdentity({ account }: { account: Account | null }) {
  const { t } = useTranslation();

  return (
    <>
      <div className="identity-name">{account?.display_name}</div>
      {account && account.hr_id !== null ? (
        <a
          className="identity-hrid"
          href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
          target="_blank"
          rel="noreferrer"
        >
          {t("home.identity.hrid", { id: account.hr_id })}
        </a>
      ) : (
        <Link className="link-button identity-hrid" to={profile()}>
          {t("home.identity.noHemaratings")}
        </Link>
      )}
    </>
  );
}
