import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { FloorDay, FloorDiscipline } from "../floorApi";
import { DayDialog } from "./DayDialog";
import { DayRow } from "./DayRow";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useKeyList,
  useSectionSave,
} from "./shared";

/** The tournament's days as a table: datum, od, do, disciplíny, přestávka.
 *  Disciplines and breaks are edited in a dialog per day; each discipline
 *  belongs to exactly one day (spec floor-setup, Days are the tournament's
 *  working windows). Where none is stored the offered day stands as a draft;
 *  a one-day tournament has one row that holds every discipline. */
export function ScheduleTab({
  slug,
  onSaved,
  onDirty,
  days,
  disciplines,
  multiDay,
}: SectionProps & {
  days: { stored: boolean; days: FloorDay[] };
  disciplines: FloorDiscipline[];
  multiDay: boolean;
}) {
  const { t } = useTranslation();
  const [draft, setDraft, changed] = useDraft(days.days, "days", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "days", onSaved);
  const errorAt = useErrorText(errors);
  const dayKeys = useKeyList(days.days.length);
  const [editing, setEditing] = useState<number | null>(null);
  // an offered default is saved as it stands, unchanged or not
  const dirty = changed || !days.stored;
  const open = editing === null ? undefined : draft[editing];

  function addDay() {
    const last = draft[draft.length - 1];
    const next = last ? nextDate(last.date) : new Date().toISOString().slice(0, 10);
    dayKeys.add();
    setDraft([
      ...draft,
      { date: next, start: "09:00", end: "19:00", breaks: [], discipline_ids: [] },
    ]);
  }

  function replace(index: number, day: FloorDay) {
    // a discipline ticked here leaves the day it was on
    const moved = new Set(day.discipline_ids);
    setDraft(
      draft.map((other, i) =>
        i === index
          ? day
          : { ...other, discipline_ids: other.discipline_ids.filter((id) => !moved.has(id)) },
      ),
    );
  }

  const placed = new Set(draft.flatMap((day) => day.discipline_ids));
  const dayless = multiDay ? disciplines.filter((d) => !placed.has(d.id)) : [];

  return (
    <SectionCard
      title={t("floor.setup.days.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      {!days.stored && <p className="muted">{t("floor.setup.days.offered")}</p>}
      <div className="floor-days-scroll">
        <table className="sheet-table floor-days">
          {/* fixed columns; what is left goes to the disciplines */}
          <colgroup>
            <col className="floor-days-date" />
            <col className="floor-days-time" />
            <col className="floor-days-time" />
            <col />
            <col className="floor-days-break" />
            <col className="floor-days-actions" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">{t("floor.setup.days.date")}</th>
              <th scope="col">{t("floor.setup.days.start")}</th>
              <th scope="col">{t("floor.setup.days.end")}</th>
              <th scope="col">{t("floor.setup.days.disciplines")}</th>
              <th scope="col">{t("floor.setup.days.break")}</th>
              <th scope="col">
                <span className="visually-hidden">{t("floor.setup.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {draft.map((day, index) => (
              <DayRow
                key={dayKeys.keys[index]}
                day={day}
                disciplines={disciplines}
                multiDay={multiDay}
                errorAt={(field) => errorAt(`${index}.${field}`)}
                onChange={(next) => setDraft(draft.map((d, i) => (i === index ? next : d)))}
                onEdit={() => setEditing(index)}
                onRemove={
                  draft.length > 1
                    ? () => {
                        dayKeys.remove(index);
                        setDraft(draft.filter((_, i) => i !== index));
                      }
                    : undefined
                }
              />
            ))}
          </tbody>
        </table>
      </div>
      <FieldNote text={errorAt("days")} />
      {dayless.length > 0 && (
        <p className="floor-missing">
          {t("floor.setup.days.dayless", { names: dayless.map((d) => d.name).join(", ") })}
        </p>
      )}
      {multiDay && (
        <button type="button" className="secondary" onClick={addDay}>
          {t("floor.setup.days.addDay")}
        </button>
      )}
      {open !== undefined && editing !== null && (
        <DayDialog
          day={open}
          days={draft}
          disciplines={disciplines}
          multiDay={multiDay}
          onChange={(next) => replace(editing, next)}
          onClose={() => setEditing(null)}
        />
      )}
    </SectionCard>
  );
}

function nextDate(date: string): string {
  const next = new Date(`${date}T12:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString().slice(0, 10);
}
