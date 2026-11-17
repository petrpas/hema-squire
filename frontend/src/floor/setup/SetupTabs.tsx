import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

/** Floor Setup's own tabs, in their order (spec floor-setup, Floor Setup has
 *  its own tabs). Which of them a tournament shows is its scope's. */
export const SETUP_TABS = [
  "scope",
  "schedule",
  "formats",
  "officials",
  "pistes",
  "params",
] as const;

export type SetupTab = (typeof SETUP_TABS)[number];

/** The small tabs across the top of floor Setup, built as office Setup's are:
 *  the same band, the same marks for something incomplete and for unsaved
 *  edits, arrows moving between tabs. */
export function SetupTabs({
  tabs,
  tab,
  incomplete,
  dirty,
  onSelect,
}: {
  tabs: SetupTab[];
  tab: SetupTab;
  incomplete: ReadonlySet<SetupTab>;
  dirty: ReadonlySet<SetupTab>;
  onSelect: (tab: SetupTab) => void;
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
    <div
      className="stage-control stage-control-band setup-tabs"
      role="tablist"
      aria-label={t("floor.setup.tabs.label")}
    >
      {tabs.map((id, index) => (
        <button
          key={id}
          type="button"
          role="tab"
          id={`floor-setup-tab-${id}`}
          aria-selected={tab === id}
          aria-controls={`floor-setup-panel-${id}`}
          tabIndex={tab === id ? 0 : -1}
          className={tab === id ? "active" : ""}
          onClick={() => onSelect(id)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          {t(`floor.setup.tabs.${id}`)}
          {incomplete.has(id) && (
            <span className="tab-mark">
              <span className="visually-hidden">{t("setup.tabs.incomplete")}</span>
            </span>
          )}
          {dirty.has(id) && (
            <span className="tab-dirty-mark">
              <span className="visually-hidden">{t("setup.tabs.unsaved")}</span>
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
