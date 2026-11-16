import { useTranslation } from "react-i18next";

import type { FloorDay } from "../floorApi";
import { FieldNote, useKeyList } from "./shared";

/** One day with its breaks. */
export function DayRow({
  day,
  errorAt,
  onChange,
  onRemove,
}: {
  day: FloorDay;
  errorAt: (field: string) => string | null;
  onChange: (day: FloorDay) => void;
  /** Absent for the last day standing: a tournament keeps at least one. */
  onRemove?: () => void;
}) {
  const { t } = useTranslation();
  const breakKeys = useKeyList(day.breaks.length);

  function setBreak(index: number, field: "start" | "end", value: string) {
    onChange({
      ...day,
      breaks: day.breaks.map((b, i) => (i === index ? { ...b, [field]: value } : b)),
    });
  }

  return (
    <div className="floor-row">
      <label>
        {t("floor.setup.days.date")}
        <input
          type="date"
          value={day.date}
          onChange={(event) => onChange({ ...day, date: event.target.value })}
        />
        <FieldNote text={errorAt("date")} />
      </label>
      <label>
        {t("floor.setup.days.start")}
        <input
          type="time"
          value={day.start}
          onChange={(event) => onChange({ ...day, start: event.target.value })}
        />
      </label>
      <label>
        {t("floor.setup.days.end")}
        <input
          type="time"
          value={day.end}
          onChange={(event) => onChange({ ...day, end: event.target.value })}
        />
        <FieldNote text={errorAt("end")} />
      </label>
      <div className="floor-breaks">
        {day.breaks.map((pause, j) => (
          <div key={breakKeys.keys[j]} className="floor-break">
            <span>{t("floor.setup.days.break")}</span>
            <input
              type="time"
              aria-label={t("floor.setup.days.breakStart")}
              value={pause.start}
              onChange={(event) => setBreak(j, "start", event.target.value)}
            />
            <input
              type="time"
              aria-label={t("floor.setup.days.breakEnd")}
              value={pause.end}
              onChange={(event) => setBreak(j, "end", event.target.value)}
            />
            <button
              type="button"
              className="secondary"
              onClick={() => {
                breakKeys.remove(j);
                onChange({ ...day, breaks: day.breaks.filter((_, k) => k !== j) });
              }}
            >
              {t("floor.setup.remove")}
            </button>
            <FieldNote text={errorAt(`breaks.${j}`) ?? errorAt(`breaks.${j}.end`)} />
          </div>
        ))}
        <button
          type="button"
          className="secondary"
          onClick={() => {
            breakKeys.add();
            onChange({ ...day, breaks: [...day.breaks, { start: "12:00", end: "13:00" }] });
          }}
        >
          {t("floor.setup.days.addBreak")}
        </button>
      </div>
      {onRemove && (
        <button type="button" className="secondary" onClick={onRemove}>
          {t("floor.setup.days.removeDay")}
        </button>
      )}
    </div>
  );
}
