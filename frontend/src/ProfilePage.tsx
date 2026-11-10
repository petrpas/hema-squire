import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { type Account, api } from "./api";
import MenuPage from "./MenuPage";
import AccountSection from "./profile/AccountSection";
import HRBoundSection from "./profile/HRBoundSection";
import HRMatchSection from "./profile/HRMatchSection";
import PrivacyTab from "./profile/PrivacyTab";
import ProfileTabs, { type ProfileTab } from "./profile/ProfileTabs";
import RoleSection from "./profile/RoleSection";

export default function ProfilePage() {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState(false);
  // the tab is in the address, so the privacy notice and a mail can lead
  // straight to the Privacy tab (routes.profile("privacy"))
  const [params, setParams] = useSearchParams();
  const tab: ProfileTab = params.get("tab") === "privacy" ? "privacy" : "profile";

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
          <ProfileTabs
            active={tab}
            onChoose={(next) =>
              setParams(next === "privacy" ? { tab: next } : {}, { replace: true })
            }
          />
          <div
            role="tabpanel"
            id={`profile-tabpanel-${tab}`}
            aria-labelledby={`profile-tab-${tab}`}
          >
            {tab === "profile" ? (
              <>
                <AccountSection account={account} onUpdated={setAccount} />
                <RoleSection account={account} />
                {account.hr_id !== null ? (
                  <HRBoundSection account={account} />
                ) : (
                  <HRMatchSection account={account} onBound={setAccount} />
                )}
              </>
            ) : (
              <PrivacyTab account={account} onUpdated={setAccount} />
            )}
          </div>
        </div>
      )}
    </MenuPage>
  );
}
