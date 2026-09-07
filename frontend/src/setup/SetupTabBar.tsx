import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import type { TournamentFlags } from "../api";
import { type SetupTab, setupTabTitleKey } from "./shared";

export function SetupTabBar({
  tabs,
  tab,
  mode,
  onSelect,
  markedTabs,
  dirtyTabs,
}: {
  tabs: SetupTab[];
  tab: SetupTab;
  /** Titles the payments tab for what it holds; the ids are unaffected. */
  mode: TournamentFlags;
  onSelect: (tab: SetupTab) => void;
  markedTabs: Set<SetupTab>;
  dirtyTabs: Set<SetupTab>;
}) {
  const { t } = useTranslation();

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = tabs[(index + step + tabs.length) % tabs.length];
    if (next) onSelect(next);
  }

  return (
    <div className="stage-control setup-tabs" role="tablist">
      {tabs.map((id, index) => (
        <button
          key={id}
          type="button"
          role="tab"
          id={`setup-tab-${id}`}
          aria-selected={tab === id}
          aria-controls={`setup-tabpanel-${id}`}
          className={tab === id ? "active" : ""}
          onClick={() => onSelect(id)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          {t(setupTabTitleKey(id, mode))}
          {markedTabs.has(id) && (
            <span className="tab-mark">
              <span className="visually-hidden">{t("setup.tabs.incomplete")}</span>
            </span>
          )}
          {dirtyTabs.has(id) && (
            <span className="tab-dirty-mark">
              <span className="visually-hidden">{t("setup.tabs.unsaved")}</span>
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
