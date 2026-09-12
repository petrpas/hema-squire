import { IconDots } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import type { Account } from "./api";
import FencerIdentity from "./FencerIdentity";
import * as routes from "./routes";
import TournamentCreateDialog, { canCreateTournament } from "./TournamentCreateDialog";

export default function AccountMenu({
  account,
  onLogout,
}: {
  account: Account | null;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const isAdmin = account !== null && (account.role === "admin" || account.is_deployment_owner);

  function close() {
    setOpen(false);
  }

  return (
    <div className="account-menu">
      <button
        type="button"
        className="account-menu-trigger"
        aria-label={t("menu.ariaLabel")}
        onClick={() => setOpen((value) => !value)}
      >
        <IconDots size={18} stroke={1.5} />
      </button>
      {open && (
        <>
          <button
            type="button"
            className="menu-backdrop"
            aria-label={t("common.close")}
            onClick={close}
          />
          <div className="account-menu-dropdown">
            {/* Shown only below 768px, where the top bar folds the identity in
                here rather than carrying it permanently in the bar. */}
            <div className="account-menu-identity">
              <FencerIdentity account={account} />
            </div>
            <Link to={routes.profile()} onClick={close}>
              {t("menu.profile")}
            </Link>
            {isAdmin && (
              <Link to={routes.admin()} onClick={close}>
                {t("menu.admin")}
              </Link>
            )}
            {/* The picker, named for what it lists: the tournaments this
                account may open a console on. Absent where there are none —
                an entry leading to an empty list is an entry that answers a
                question nobody asked, and the way to a first tournament is
                the create entry below, not this one. There is no entry back
                to the fencer's own screens: the logo is that, on every page
                and without opening a menu. */}
            {account !== null && account.organized_count > 0 && (
              <Link to={routes.picker()} onClick={close}>
                {t("menu.myTournaments")}
              </Link>
            )}
            {/* Offered from the menu so an organizer reaches creation from any
                screen rather than only from the picker (spec
                `tournament-admin`). Not shown at all below the Organizer
                role — the entry states what the account may do. */}
            {canCreateTournament(account) && (
              <button
                type="button"
                onClick={() => {
                  close();
                  setCreating(true);
                }}
              >
                {t("menu.createTournament")}
              </button>
            )}
            <button
              type="button"
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
      {creating && (
        <TournamentCreateDialog
          onClose={() => setCreating(false)}
          onDone={(tournament) => {
            setCreating(false);
            navigate(routes.consolePath(tournament.slug, "setup"));
          }}
        />
      )}
    </div>
  );
}
