import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

/** The tournament's dates, in chronological order. Order is fixed by meaning
 *  rather than by which fields are filled, so an unset date keeps its place
 *  and the shape of the timeline does not move as it is filled in (design
 *  regroup-setup-parameters Decision 3).
 *
 *  Every hint states the field's fallback: each falls back to something
 *  different, and without it the organizer cannot tell "not set" from "not
 *  applicable" (Decision 4). */
const TIMELINE_FIELDS = [
  { key: "registration_opens", hint: "setup.timeline.opensHint" },
  { key: "seating_deadline", hint: "setup.timeline.seatingHint" },
  { key: "registration_closes", hint: "setup.timeline.closesHint" },
] as const;

/** The seating deadline is offered only while payments are on: nothing
 *  settles against it when no money is owed (spec: setup-navigation). The
 *  registration window is offered in every mode. */
const SEATING_FIELD = "seating_deadline";

const COMPOSITION_FIELD = {
  key: "team_composition_deadline",
  hint: "setup.timeline.compositionHint",
} as const;

export function TimelineSection({
  detail,
  slug,
  registry,
  hasTeamDiscipline,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
  /** Whether any discipline is of the team kind, including a row added in the
   *  current unsaved DISCIPLINES draft — lifted through SetupPanel, since the
   *  rows and this field no longer share a component (design Decision 3a). */
  hasTeamDiscipline: boolean;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  // A stored date whose field is not offered is retained, never cleared: the
  // flush below writes only the fields actually shown.
  const shownTimelineFields = TIMELINE_FIELDS.filter(
    (field) => field.key !== SEATING_FIELD || detail.feature_payments,
  );
  const fields =
    hasTeamDiscipline && detail.feature_teams
      ? [...shownTimelineFields, COMPOSITION_FIELD]
      : shownTimelineFields;

  useEffect(() => {
    setValues({
      registration_opens: detail.registration_opens ?? "",
      seating_deadline: detail.seating_deadline ?? "",
      registration_closes: detail.registration_closes ?? "",
      team_composition_deadline: detail.team_composition_deadline ?? "",
    });
    validation.clearAll();
    setError(null);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  useSectionSaver(registry, "timeline", "timeline", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    // dates are typed by the browser's own date input; the cross-field rules
    // (seating deadline within the registration close) are the backend's, and
    // surface here through applyApiErrors rather than being restated
    validate: () => 0,
    focusFirstInvalid: () => {},
    flush: async () => {
      try {
        // Only the fields on show are written. A stored date whose field the
        // mode conceals — the seating deadline with payments off, the
        // composition deadline with the team feature off or with no team
        // discipline left — is retained, not cleared (spec: "Stored deadline
        // survives removing the team discipline").
        const patch: Record<string, unknown> = {};
        for (const field of fields) {
          patch[field.key] = values[field.key] || null;
        }
        await api.updateTournament(slug, patch);
        setDirty(false);
        return [{ change: "timeline", section: "timeline", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setError(message);
        return [{ change: "timeline", section: "timeline", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.timeline.title")}</h2>
      <div className="form-fields">
        {fields.map((field) => (
          <label key={field.key} className="form-field">
            <span>
              {t(`param.${field.key}`)}
              <HelpHint text={t(field.hint)} />
            </span>
            <input
              ref={(el) => {
                fieldRefs.current[field.key] = el;
              }}
              type="date"
              value={values[field.key] ?? ""}
              onChange={(event) => {
                setValues({ ...values, [field.key]: event.target.value });
                setDirty(true);
                // these fields carry backend rejections only (the cross-date
                // rules), so editing clears a stale one rather than re-checking
                validation.clearIfValid(field.key, () => null);
              }}
              {...invalidProps(field.key, validation.errors[field.key])}
            />
            <FieldError field={field.key} error={validation.errors[field.key]} />
          </label>
        ))}
      </div>
      {/* the anchor the other dates run towards; editable only on TOURNAMENT,
          so the field keeps exactly one editor */}
      <p className="rail-hint">
        {t("setup.timeline.anchor", { date: new Date(detail.date).toLocaleDateString("cs") })}
      </p>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
