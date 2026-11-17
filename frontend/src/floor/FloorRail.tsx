import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { type FloorTab, TAB_ICONS } from "./tabs";

/** The floor console's tabs as a rail of icons down the left edge (spec
 *  floor-console, The tabs are a rail of icons on the left). A tab's name is
 *  its hint, shown on hover and focus, and its accessible name; a badge and
 *  the unsaved mark sit on the icon and are said in words. Up and down move
 *  between tabs. */
export function FloorRail({
  tabs,
  tab,
  badges,
  dirty,
  onSelect,
}: {
  tabs: FloorTab[];
  tab: FloorTab;
  badges: Record<string, boolean>;
  /** The tab holding unsaved changes, marked as Setup marks its own. */
  dirty: FloorTab | null;
  onSelect: (tab: FloorTab) => void;
}) {
  const { t } = useTranslation();

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = tabs[(index + step + tabs.length) % tabs.length];
    if (next) onSelect(next);
  }

  return (
    <nav className="floor-rail">
      {/* the list is its own element: a `nav` may not take the tablist role */}
      <div
        className="floor-rail-list"
        role="tablist"
        aria-orientation="vertical"
        aria-label={t("floor.tabs.label")}
      >
        {tabs.map((id, index) => {
          const Icon = TAB_ICONS[id];
          const waiting = badges[id] === true;
          const unsaved = dirty === id;
          const name = [
            t(`floor.tabs.${id}`),
            waiting ? t("floor.tabs.waiting") : null,
            unsaved ? t("setup.tabs.unsaved") : null,
          ]
            .filter((part) => part !== null)
            .join(", ");
          return (
            <button
              key={id}
              type="button"
              role="tab"
              id={`floor-tab-${id}`}
              aria-selected={tab === id}
              aria-controls={`floor-tabpanel-${id}`}
              aria-label={name}
              tabIndex={tab === id ? 0 : -1}
              className={tab === id ? "active" : ""}
              onClick={() => onSelect(id)}
              onKeyDown={(event) => onKeyDown(event, index)}
            >
              <Icon size={22} stroke={1.5} aria-hidden="true" />
              {waiting && <span className="floor-rail-badge" />}
              {unsaved && <span className="tab-dirty-mark" />}
              <span className="floor-rail-hint" aria-hidden="true">
                {name}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
