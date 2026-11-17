import { useTranslation } from "react-i18next";

import type { FloorScope } from "../floorApi";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
} from "./shared";

/** What the floor plans: three ticks that decide what the rest of Setup and
 *  the console show (spec floor-setup, Scope decides what is planned). Turning
 *  one off hides what it governs and deletes nothing. */
export function ScopeTab({ slug, onSaved, onDirty, scope }: SectionProps & { scope: FloorScope }) {
  const { t } = useTranslation();
  const [draft, setDraft, dirty] = useDraft(scope, "scope", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "scope", onSaved);
  const errorAt = useErrorText(errors);

  function schedule(on: boolean) {
    // several days and the officials both need the schedule
    setDraft(
      on
        ? { ...draft, plan_schedule: true }
        : { plan_schedule: false, multi_day: false, plan_officials: false },
    );
  }

  return (
    <SectionCard
      title={t("floor.setup.scope.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      <div className="floor-scope">
        <div className="floor-scope-item">
          <label className="floor-check">
            <input
              type="checkbox"
              checked={draft.plan_schedule}
              onChange={(event) => schedule(event.target.checked)}
            />
            {t("floor.setup.scope.plan_schedule")}
          </label>
          <p className="muted">{t("floor.setup.scope.plan_scheduleHint")}</p>
        </div>
        <div className="floor-scope-item floor-nested">
          <label className="floor-check">
            <input
              type="checkbox"
              checked={draft.multi_day}
              disabled={!draft.plan_schedule}
              onChange={(event) => setDraft({ ...draft, multi_day: event.target.checked })}
            />
            {t("floor.setup.scope.multi_day")}
          </label>
          <FieldNote text={errorAt("multi_day")} />
        </div>
        <div className="floor-scope-item">
          <label className="floor-check">
            <input
              type="checkbox"
              checked={draft.plan_officials}
              disabled={!draft.plan_schedule}
              onChange={(event) => setDraft({ ...draft, plan_officials: event.target.checked })}
            />
            {t("floor.setup.scope.plan_officials")}
          </label>
          {!draft.plan_schedule && (
            <p className="muted">{t("floor.setup.scope.officialsNeedSchedule")}</p>
          )}
          <FieldNote text={errorAt("plan_officials")} />
        </div>
      </div>
    </SectionCard>
  );
}
