import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

export type AdminTab = "tasks" | "people" | "tournaments";

const TABS: AdminTab[] = ["tasks", "people", "tournaments"];

/** The admin panel's three tabs (spec user-roles, Admin panel). The tasks tab
 *  carries the count of open items; arrows move between tabs as they do on
 *  the payments console's strip. */
export default function AdminTabs({
  active,
  openTasks,
  onChoose,
}: {
  active: AdminTab;
  openTasks: number;
  onChoose: (tab: AdminTab) => void;
}) {
  const { t } = useTranslation();

  function move(index: number, event: KeyboardEvent<HTMLButtonElement>) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = TABS[(index + step + TABS.length) % TABS.length];
    if (next) {
      onChoose(next);
      document.getElementById(`admin-tab-${next}`)?.focus();
    }
  }

  return (
    <div
      className="stage-control stage-control-band admin-tabs"
      role="tablist"
      aria-label={t("admin.tabs.label")}
    >
      {TABS.map((tab, index) => (
        <button
          key={tab}
          type="button"
          role="tab"
          id={`admin-tab-${tab}`}
          aria-selected={tab === active}
          aria-controls={`admin-tabpanel-${tab}`}
          tabIndex={tab === active ? 0 : -1}
          className={tab === active ? "active" : ""}
          onClick={() => onChoose(tab)}
          onKeyDown={(event) => move(index, event)}
        >
          {t(`admin.tabs.${tab}`)}
          {tab === "tasks" && <span className="tab-count">{openTasks}</span>}
        </button>
      ))}
    </div>
  );
}
