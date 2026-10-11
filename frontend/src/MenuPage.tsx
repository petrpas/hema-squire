import { IconX } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { Account } from "./api";
import { useAuth } from "./RequireAuth";
import TopBar from "./TopBar";
import usePageClose from "./usePageClose";

/** A page reached from the account menu — the Profile page, the admin panel,
 *  the tournament picker.
 *  It carries the same top bar as the fencer's screens, whose application name
 *  leads to the tournament list, and a close control on its card that returns
 *  to wherever it was opened from, as Escape does. */
export default function MenuPage({
  title,
  account,
  night = false,
  wide = true,
  children,
}: {
  title: string;
  account: Account | null;
  /** The Profile page is night and the admin panel day (spec design-system,
   *  Skins); the page sets it on its root, as FencerShell does. */
  night?: boolean;
  /** A wide card scrolls its own body and, on a phone, is the screen below
   *  the bar; a narrow one is a card resting on the page, which scrolls. */
  wide?: boolean;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const { onLogout } = useAuth();
  const close = usePageClose();

  return (
    <div className="app" data-skin={night ? "night" : undefined}>
      <TopBar account={account} signedIn={true} onLogout={onLogout} />
      <div className={`login-page page-under-bar${wide ? " page-under-bar-wide" : ""}`}>
        <div className={wide ? "login-card wide-card" : "login-card"}>
          <div className="page-card-head">
            <h1>{title}</h1>
            <button
              type="button"
              className="row-action"
              title={t("common.close")}
              aria-label={t("common.close")}
              onClick={close}
            >
              <IconX size={18} stroke={1.5} />
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
