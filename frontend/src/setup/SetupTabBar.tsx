import { type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { type TournamentMode } from "../api";
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
  mode: TournamentMode;
  onSelect: (tab: SetupTab) => void;
  markedTabs: Set<SetupTab>;
  dirtyTabs: Set<SetupTab>;
}) {
  const { t } = useTranslation();

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      onSelect(tabs[(index + 1) % tabs.length]);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      onSelect(tabs[(index - 1 + tabs.length) % tabs.length]);
    }
  }

  return (
    <nav className="stage-control setup-tabs" role="tablist">
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
    </nav>
  );
}
