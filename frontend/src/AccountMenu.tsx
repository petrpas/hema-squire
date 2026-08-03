import { IconDots } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { type Account } from "./api";
import * as routes from "./routes";

export default function AccountMenu({
  account,
  onLogout,
}: {
  account: Account | null;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const isAdmin = account !== null && (account.role === "admin" || account.is_deployment_owner);

  function close() {
    setOpen(false);
  }

  return (
    <div className="account-menu">
      <button
        className="account-menu-trigger"
        aria-label={t("menu.ariaLabel")}
        onClick={() => setOpen((value) => !value)}
      >
        <IconDots size={18} stroke={1.5} />
      </button>
      {open && (
        <>
          <div className="menu-backdrop" onClick={close} />
          <div className="account-menu-dropdown">
            <Link to={routes.profile()} onClick={close}>
              {t("menu.profile")}
            </Link>
            {isAdmin && (
              <Link to={routes.admin()} onClick={close}>
                {t("menu.admin")}
              </Link>
            )}
            <Link to={routes.home()} onClick={close}>
              {t("menu.toFencer")}
            </Link>
            <Link to={routes.picker()} onClick={close}>
              {t("menu.toOrganizer")}
            </Link>
            <button
              onClick={() => {
                close();
                onLogout();
              }}
            >
              {t("menu.logout")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
