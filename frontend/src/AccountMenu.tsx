import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, setToken } from "./api";

export default function AccountMenu({
  account,
  onProfile,
  onAdmin,
  onFencer,
  onOrganizer,
  onLogout,
}: {
  account: Account | null;
  onProfile: () => void;
  onAdmin: () => void;
  onFencer: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const isAdmin = account !== null && (account.role === "admin" || account.is_deployment_owner);

  function select(action: () => void) {
    setOpen(false);
    action();
  }

  return (
    <div className="account-menu">
      <button
        className="account-menu-trigger"
        aria-label={t("menu.ariaLabel")}
        onClick={() => setOpen((value) => !value)}
      >
        ⋯
      </button>
      {open && (
        <>
          <div className="menu-backdrop" onClick={() => setOpen(false)} />
          <div className="account-menu-dropdown">
            <button onClick={() => select(onProfile)}>{t("menu.profile")}</button>
            {isAdmin && <button onClick={() => select(onAdmin)}>{t("menu.admin")}</button>}
            <button onClick={() => select(onFencer)}>{t("menu.toFencer")}</button>
            <button onClick={() => select(onOrganizer)}>{t("menu.toOrganizer")}</button>
            <button
              onClick={() =>
                select(() => {
                  setToken(null);
                  onLogout();
                })
              }
            >
              {t("menu.logout")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
