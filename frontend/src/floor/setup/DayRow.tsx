import { IconPencil, IconTrash } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { FloorDay, FloorDiscipline } from "../floorApi";
import { FieldNote, weekday } from "./shared";

/** One day as a table row. Its disciplines and breaks read as text; both are
 *  edited in the day's dialog. */
export function DayRow({
  day,
  disciplines,
  multiDay,
  errorAt,
  onChange,
  onEdit,
  onRemove,
}: {
  day: FloorDay;
  disciplines: FloorDiscipline[];
  multiDay: boolean;
  errorAt: (field: string) => string | null;
  onChange: (day: FloorDay) => void;
  onEdit: () => void;
  /** Absent for the last day standing: a tournament keeps at least one. */
  onRemove?: () => void;
}) {
  const { t, i18n } = useTranslation();
  const names = disciplines.filter((d) => day.discipline_ids.includes(d.id)).map((d) => d.name);
  const held = multiDay ? names.join(", ") || "—" : t("floor.setup.days.all");
  // one break per line: a comma at a wrapped line's end reads as a stray mark
  const breaks =
    day.breaks.length === 0
      ? t("floor.setup.days.noBreak")
      : day.breaks.map((pause) => (
          <span key={`${pause.start}-${pause.end}`} className="floor-days-break-line">
            {pause.start}–{pause.end}
          </span>
        ));
  const breakError = day.breaks
    .map((_, j) => errorAt(`breaks.${j}`) ?? errorAt(`breaks.${j}.end`))
    .find((text) => text !== null);
  const disciplineError = day.discipline_ids
    .map((_, j) => errorAt(`discipline_ids.${j}`))
    .find((text) => text !== null);

  return (
    <tr>
      <td>
        <div className="floor-day-date">
          <span className="floor-weekday">{weekday(day.date, i18n.language)}</span>
          <input
            type="date"
            aria-label={t("floor.setup.days.date")}
            value={day.date}
            aria-invalid={errorAt("date") !== null}
            onChange={(event) => onChange({ ...day, date: event.target.value })}
          />
        </div>
        <FieldNote text={errorAt("date")} />
      </td>
      <td>
        <input
          type="time"
          aria-label={t("floor.setup.days.start")}
          value={day.start}
          onChange={(event) => onChange({ ...day, start: event.target.value })}
        />
      </td>
      <td>
        <input
          type="time"
          aria-label={t("floor.setup.days.end")}
          value={day.end}
          aria-invalid={errorAt("end") !== null}
          onChange={(event) => onChange({ ...day, end: event.target.value })}
        />
        <FieldNote text={errorAt("end")} />
      </td>
      <td className="floor-days-text">
        {held}
        <FieldNote text={disciplineError ?? null} />
      </td>
      <td className="floor-days-text">
        {breaks}
        <FieldNote text={breakError ?? null} />
      </td>
      <td>
        <div className="row-actions">
          <button
            type="button"
            className="row-action"
            title={t("floor.setup.edit")}
            onClick={onEdit}
          >
            <IconPencil size={16} stroke={1.5} aria-hidden="true" />
            <span className="visually-hidden">{t("floor.setup.edit")}</span>
          </button>
          {onRemove && (
            <button
              type="button"
              className="row-action"
              title={t("floor.setup.days.removeDay")}
              onClick={onRemove}
            >
              <IconTrash size={16} stroke={1.5} aria-hidden="true" />
              <span className="visually-hidden">{t("floor.setup.days.removeDay")}</span>
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
