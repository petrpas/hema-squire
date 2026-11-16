import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { useTabBand } from "../useTabBand";
import type { FloorBarTab } from "./tabs";

/** The floor console's band. A badge is a static mark meaning "something here
 *  is waiting for you" (spec floor-console); an unbadged tab looks like every
 *  other unbadged tab. Built as Setup's tab bar is, arrows moving between
 *  tabs. */
export function FloorTabBar({
  tabs,
  tab,
  badges,
  dirty,
  onSelect,
}: {
  tabs: FloorBarTab[];
  tab: FloorBarTab;
  badges: Record<string, boolean>;
  /** The tab holding unsaved changes, marked as Setup marks its own. */
  dirty: FloorBarTab | null;
  onSelect: (tab: FloorBarTab) => void;
}) {
  const { t } = useTranslation();
  const band = useTabBand(tab);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = tabs[(index + step + tabs.length) % tabs.length];
    if (next) onSelect(next);
  }

  return (
    <nav ref={band} className="stage-control stage-control-band floor-tabs">
      {/* the list is its own element: a `nav` may not take the tablist role,
       and the band's scrolling hook wants the scrolling element */}
      <div className="floor-tablist" role="tablist" aria-label={t("floor.tabs.label")}>
        {tabs.map((id, index) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`floor-tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`floor-tabpanel-${id}`}
            className={tab === id ? "active" : ""}
            onClick={() => onSelect(id)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {t(`floor.tabs.${id}`)}
            {badges[id] === true && (
              <span className="tab-mark">
                <span className="visually-hidden">{t("floor.tabs.waiting")}</span>
              </span>
            )}
            {dirty === id && (
              <span className="tab-dirty-mark">
                <span className="visually-hidden">{t("setup.tabs.unsaved")}</span>
              </span>
            )}
          </button>
        ))}
      </div>
    </nav>
  );
}
