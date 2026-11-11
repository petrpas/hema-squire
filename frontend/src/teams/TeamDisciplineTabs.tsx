import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import type { ConsoleTeamDiscipline } from "../api";

/** The team disciplines as tabs under the Teams heading, each counting its
 *  teams. Drawn only where there are two or more: most tournaments hold one
 *  team discipline, and a tab bar of one tab says nothing. */
export default function TeamDisciplineTabs({
  disciplines,
  active,
  onSelect,
}: {
  disciplines: ConsoleTeamDiscipline[];
  active: string;
  onSelect: (slug: string) => void;
}) {
  const { t } = useTranslation();

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = disciplines[(index + step + disciplines.length) % disciplines.length];
    if (next) onSelect(next.slug);
  }

  return (
    <div
      className="stage-control team-discipline-tabs"
      role="tablist"
      aria-label={t("teams.column.discipline")}
    >
      {disciplines.map((discipline, index) => (
        <button
          key={discipline.slug}
          type="button"
          role="tab"
          aria-selected={discipline.slug === active}
          className={discipline.slug === active ? "active" : ""}
          onClick={() => onSelect(discipline.slug)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          {discipline.name || discipline.slug}
          <span className="tab-count">{discipline.teams.length}</span>
        </button>
      ))}
    </div>
  );
}
