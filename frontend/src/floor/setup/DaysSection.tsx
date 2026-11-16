import { useTranslation } from "react-i18next";

import type { FloorDay } from "../floorApi";
import { DayRow } from "./DayRow";
import {
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useKeyList,
  useSectionSave,
} from "./shared";

/** The tournament's days: date, start, end and fixed breaks, in the
 *  tournament's own wall clock (spec floor-setup, Days are the tournament's
 *  working windows). Where none is stored the offered day stands as a draft. */
export function DaysSection({
  slug,
  onSaved,
  onDirty,
  days,
}: SectionProps & { days: { stored: boolean; days: FloorDay[] } }) {
  const { t } = useTranslation();
  const [draft, setDraft, changed] = useDraft(days.days, "days", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "days", onSaved);
  const errorAt = useErrorText(errors);
  const dayKeys = useKeyList(days.days.length);
  // an offered default is saved as it stands, unchanged or not
  const dirty = changed || !days.stored;

  function addDay() {
    const last = draft[draft.length - 1];
    const next = last ? nextDate(last.date) : new Date().toISOString().slice(0, 10);
    dayKeys.add();
    setDraft([...draft, { date: next, start: "09:00", end: "19:00", breaks: [] }]);
  }

  return (
    <SectionCard
      title={t("floor.setup.days.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      {!days.stored && <p className="muted">{t("floor.setup.days.offered")}</p>}
      {draft.map((day, index) => (
        <DayRow
          key={dayKeys.keys[index]}
          day={day}
          errorAt={(field) => errorAt(`${index}.${field}`)}
          onChange={(next) => setDraft(draft.map((d, i) => (i === index ? next : d)))}
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
      <button type="button" className="secondary" onClick={addDay}>
        {t("floor.setup.days.addDay")}
      </button>
    </SectionCard>
  );
}

function nextDate(date: string): string {
  const next = new Date(`${date}T12:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString().slice(0, 10);
}
