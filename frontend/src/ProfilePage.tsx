import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, api } from "./api";
import MenuPage from "./MenuPage";
import AccountSection from "./profile/AccountSection";
import HRBoundSection from "./profile/HRBoundSection";
import HRMatchSection from "./profile/HRMatchSection";
import RoleSection from "./profile/RoleSection";

export default function ProfilePage() {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.account().then(setAccount, () => setError(true));
  }, []);

  // Night, for every account that opens it: a fencer arrives from the night
  // list's menu, and the skin follows the route, not the role (spec
  // profile-page).
  return (
    <MenuPage title={t("profile.title")} account={account} night>
      {error ? (
        <p className="login-error">{t("profile.loadFailed")}</p>
      ) : account === null ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="page-card-body">
          <AccountSection account={account} onUpdated={setAccount} />
          <RoleSection account={account} />
          {account.hr_id !== null ? (
            <HRBoundSection account={account} />
          ) : (
            <HRMatchSection account={account} onBound={setAccount} />
          )}
        </div>
      )}
    </MenuPage>
  );
}
