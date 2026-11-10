import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

export type ProfileTab = "profile" | "privacy";

export const PROFILE_TABS: ProfileTab[] = ["profile", "privacy"];

/** The Profile page's two tabs: who the account is, and everything about its
 *  personal data in one place (spec `profile-page`). Arrows move between them
 *  as on the admin panel's strip. */
export default function ProfileTabs({
  active,
  onChoose,
}: {
  active: ProfileTab;
  onChoose: (tab: ProfileTab) => void;
}) {
  const { t } = useTranslation();

  function move(index: number, event: KeyboardEvent<HTMLButtonElement>) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = PROFILE_TABS[(index + step + PROFILE_TABS.length) % PROFILE_TABS.length];
    if (next) {
      onChoose(next);
      document.getElementById(`profile-tab-${next}`)?.focus();
    }
  }

  return (
    <div
      className="stage-control stage-control-band admin-tabs"
      role="tablist"
      aria-label={t("profile.tabs.label")}
    >
      {PROFILE_TABS.map((tab, index) => (
        <button
          key={tab}
          type="button"
          role="tab"
          id={`profile-tab-${tab}`}
          aria-selected={tab === active}
          aria-controls={`profile-tabpanel-${tab}`}
          tabIndex={tab === active ? 0 : -1}
          className={tab === active ? "active" : ""}
          onClick={() => onChoose(tab)}
          onKeyDown={(event) => move(index, event)}
        >
          {t(`profile.tabs.${tab}`)}
        </button>
      ))}
    </div>
  );
}
