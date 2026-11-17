import { IconPlus, IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import type { FloorDay, FloorDiscipline } from "../floorApi";
import { dayLabel, useKeyList, weekday } from "./shared";

/** One day's disciplines and breaks, ticked in a dialog (spec floor-setup,
 *  Days are the tournament's working windows). A discipline already on
 *  another day is named with that day, and ticking it here moves it. What is
 *  chosen is the Rozvrh tab's draft: closing saves nothing. */
export function DayDialog({
  day,
  days,
  disciplines,
  multiDay,
  onChange,
  onClose,
}: {
  day: FloorDay;
  days: FloorDay[];
  disciplines: FloorDiscipline[];
  multiDay: boolean;
  onChange: (day: FloorDay) => void;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const breakKeys = useKeyList(day.breaks.length);

  function elsewhere(discipline: number): string | null {
    const other = days.find((d) => d !== day && d.discipline_ids.includes(discipline));
    return other ? dayLabel(other.date, i18n.language) : null;
  }

  function tick(discipline: number, on: boolean) {
    const ids = on
      ? [...day.discipline_ids, discipline]
      : day.discipline_ids.filter((id) => id !== discipline);
    onChange({ ...day, discipline_ids: ids });
  }

  function setBreak(index: number, field: "start" | "end", value: string) {
    onChange({
      ...day,
      breaks: day.breaks.map((b, i) => (i === index ? { ...b, [field]: value } : b)),
    });
  }

  const title = `${weekday(day.date, i18n.language)} ${new Date(
    `${day.date}T12:00:00`,
  ).toLocaleDateString(i18n.language, { day: "numeric", month: "numeric", year: "numeric" })}`;

  return (
    <Modal onClose={onClose}>
      <div className="modal floor-day-dialog">
        <h2>{title}</h2>
        {multiDay && (
          <fieldset className="floor-day-section">
            <legend>{t("floor.setup.days.disciplines")}</legend>
            {disciplines.map((discipline) => {
              const other = elsewhere(discipline.id);
              return (
                <label key={discipline.id} className="floor-day-tick">
                  <input
                    type="checkbox"
                    checked={day.discipline_ids.includes(discipline.id)}
                    onChange={(event) => tick(discipline.id, event.target.checked)}
                  />
                  <span>{discipline.name}</span>
                  {other !== null && (
                    <span className="muted">{t("floor.setup.days.onDay", { day: other })}</span>
                  )}
                </label>
              );
            })}
          </fieldset>
        )}
        <fieldset className="floor-day-section">
          <legend>{t("floor.setup.days.breaks")}</legend>
          {day.breaks.length === 0 && <p className="muted">{t("floor.setup.days.noBreak")}</p>}
          {day.breaks.map((pause, j) => (
            <div key={breakKeys.keys[j]} className="floor-break">
              <input
                type="time"
                aria-label={t("floor.setup.days.breakStart")}
                value={pause.start}
                onChange={(event) => setBreak(j, "start", event.target.value)}
              />
              <span aria-hidden="true">–</span>
              <input
                type="time"
                aria-label={t("floor.setup.days.breakEnd")}
                value={pause.end}
                onChange={(event) => setBreak(j, "end", event.target.value)}
              />
              <button
                type="button"
                className="row-action"
                title={t("floor.setup.days.removeBreak")}
                onClick={() => {
                  breakKeys.remove(j);
                  onChange({ ...day, breaks: day.breaks.filter((_, k) => k !== j) });
                }}
              >
                <IconX size={16} stroke={1.5} aria-hidden="true" />
                <span className="visually-hidden">{t("floor.setup.days.removeBreak")}</span>
              </button>
            </div>
          ))}
          <button
            type="button"
            className="link-button floor-day-add"
            onClick={() => {
              breakKeys.add();
              onChange({ ...day, breaks: [...day.breaks, { start: "12:00", end: "13:00" }] });
            }}
          >
            <IconPlus size={14} stroke={1.5} aria-hidden="true" />
            {t("floor.setup.days.addBreak")}
          </button>
        </fieldset>
        <div className="modal-actions floor-day-actions">
          <button type="button" className="btn-primary" onClick={onClose}>
            {t("floor.setup.done")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
