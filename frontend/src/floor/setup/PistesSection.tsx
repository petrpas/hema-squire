import { useTranslation } from "react-i18next";

import type { FloorPiste } from "../floorApi";
import {
  DayTicks,
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
} from "./shared";

/** The pistes in their display order: name, the days each is available, the
 *  reserve mark and an optional tag (spec floor-setup, Pistes and their
 *  availability). */
export function PistesSection({
  slug,
  onSaved,
  onDirty,
  pistes,
  days,
}: SectionProps & { pistes: FloorPiste[]; days: string[] }) {
  const { t } = useTranslation();
  const [draft, setDraft, dirty] = useDraft(pistes, "pistes", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "pistes", onSaved);
  const errorAt = useErrorText(errors);

  function patch(index: number, fields: Partial<FloorPiste>) {
    setDraft(draft.map((piste, i) => (i === index ? { ...piste, ...fields } : piste)));
  }

  function move(index: number, by: -1 | 1) {
    const other = index + by;
    const a = draft[index];
    const b = draft[other];
    if (a === undefined || b === undefined) return;
    const next = [...draft];
    next[index] = b;
    next[other] = a;
    setDraft(next);
  }

  const reserve = draft.filter((piste) => piste.reserve).length;

  return (
    <SectionCard
      title={t("floor.setup.pistes.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      {draft.length > 0 && (
        <p className="muted">
          {t("floor.setup.pistes.planned", { count: draft.length - reserve })}
          {reserve > 0 && ` ${t("floor.setup.pistes.held", { count: reserve })}`}
        </p>
      )}
      {draft.map((piste, index) => (
        <div key={piste.id ?? `new-${index}`} className="floor-row">
          <label>
            {t("floor.setup.pistes.name")}
            <input
              value={piste.name}
              maxLength={80}
              onChange={(event) => patch(index, { name: event.target.value })}
            />
            <FieldNote text={errorAt(`${index}.name`)} />
          </label>
          <label>
            {t("floor.setup.pistes.tag")}
            <input
              value={piste.tag ?? ""}
              maxLength={80}
              placeholder={t("floor.setup.pistes.tagHint")}
              onChange={(event) => patch(index, { tag: event.target.value || null })}
            />
          </label>
          <label className="floor-check">
            <input
              type="checkbox"
              checked={piste.reserve}
              onChange={(event) => patch(index, { reserve: event.target.checked })}
            />
            {t("floor.setup.pistes.reserve")}
          </label>
          {days.length > 1 && (
            <DayTicks
              days={days}
              chosen={piste.days}
              label={t("floor.setup.pistes.days")}
              onChange={(chosen) => patch(index, { days: chosen })}
            />
          )}
          <FieldNote text={errorAt(`${index}.days.0`)} />
          <div className="floor-row-actions">
            <button
              type="button"
              className="secondary"
              aria-label={t("actions.moveUp")}
              disabled={index === 0}
              onClick={() => move(index, -1)}
            >
              ↑
            </button>
            <button
              type="button"
              className="secondary"
              aria-label={t("floor.setup.moveDown")}
              disabled={index === draft.length - 1}
              onClick={() => move(index, 1)}
            >
              ↓
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setDraft(draft.filter((_, i) => i !== index))}
            >
              {t("floor.setup.remove")}
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="secondary"
        onClick={() =>
          setDraft([
            ...draft,
            { id: null, name: String(draft.length + 1), reserve: false, tag: null, days },
          ])
        }
      >
        {t("floor.setup.pistes.add")}
      </button>
    </SectionCard>
  );
}
