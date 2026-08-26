import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

/** The zone a tournament is given when it has not chosen one — the launch
 *  market's, matching the backend default (app.constraints). */
const DEFAULT_TIMEZONE = "Europe/Prague";

/** The tournament's dates, in chronological order. Order is fixed by meaning
 *  rather than by which fields are filled, so an unset date keeps its place
 *  and the shape of the timeline does not move as it is filled in (design
 *  regroup-setup-parameters Decision 3).
 *
 *  Every hint states the field's fallback: each falls back to something
 *  different, and without it the organizer cannot tell "not set" from "not
 *  applicable" (Decision 4). */
const TIMELINE_FIELDS = [
  {
    key: "registration_opens",
    hint: "setup.timeline.opensHint",
    // the opening carries a clock time, the only date on the timeline that
    // does: it is a starting gun, not a deadline (design
    // add-registration-open-time D3). The time renders inside this field
    // rather than as a row of its own, so it reads as a qualifier of the date
    // and does not take a place in the chronological sequence
    time: "registration_opens_time",
  },
  { key: "seating_deadline", hint: "setup.timeline.seatingHint" },
  { key: "registration_closes", hint: "setup.timeline.closesHint" },
] as const;

/** The zone every date and time on this timeline is read in. Offered from the
 *  browser's own zone database rather than a hand-kept list, filtered to the
 *  continent the tournaments are on; the stored value is always among the
 *  choices, so a zone set through the API is never silently rewritten by
 *  opening Setup (design D9). */
function timezoneChoices(stored: string): string[] {
  // ES2022 and not in this project's `lib`, so it is reached through a narrow
  // declaration rather than by widening the whole compilation's target
  const { supportedValuesOf } = Intl as {
    supportedValuesOf?: (key: string) => string[];
  };
  const supported = supportedValuesOf ? supportedValuesOf("timeZone") : [];
  const european = supported.filter((zone) => zone.startsWith("Europe/"));
  const choices = european.length > 0 ? european : [DEFAULT_TIMEZONE];
  return choices.includes(stored) ? choices : [stored, ...choices];
}

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
      // the stored value carries seconds the organizer never typed; the input
      // takes HH:MM and the backend fills the rest back in
      registration_opens_time: (detail.registration_opens_time ?? "").slice(0, 5),
      seating_deadline: detail.seating_deadline ?? "",
      registration_closes: detail.registration_closes ?? "",
      team_composition_deadline: detail.team_composition_deadline ?? "",
      timezone: detail.timezone,
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
          if ("time" in field) {
            // the time goes with its date in the same save, so the two can
            // never reach the system separately with an inconsistent state
            // between them (spec: setup-navigation)
            patch[field.time] = values[field.key] ? values[field.time] || null : null;
          }
        }
        patch.timezone = values.timezone;
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
            <div className="field-pair">
              <input
                ref={(el) => {
                  fieldRefs.current[field.key] = el;
                }}
                type="date"
                value={values[field.key] ?? ""}
                onChange={(event) => {
                  setValues({
                    ...values,
                    [field.key]: event.target.value,
                    // clearing the date clears its time: a time with no date
                    // is not a state the organizer could see or correct
                    // (design D9), and the backend refuses it
                    ...("time" in field && !event.target.value ? { [field.time]: "" } : {}),
                  });
                  setDirty(true);
                  // these fields carry backend rejections only (the cross-date
                  // rules), so editing clears a stale one rather than re-checking
                  validation.clearIfValid(field.key, () => null);
                }}
                {...invalidProps(field.key, validation.errors[field.key])}
              />
              {/* no hint of its own: the field's one hint covers both halves,
                  and a second marker here would open its window past the edge
                  of the panel, which clips horizontally */}
              {"time" in field && (
                <input
                  ref={(el) => {
                    fieldRefs.current[field.time] = el;
                  }}
                  type="time"
                  className="field-time"
                  aria-label={t(`param.${field.time}`)}
                  value={values[field.time] ?? ""}
                  onChange={(event) => {
                    setValues({ ...values, [field.time]: event.target.value });
                    setDirty(true);
                    validation.clearIfValid(field.time, () => null);
                  }}
                  {...invalidProps(field.time, validation.errors[field.time])}
                />
              )}
            </div>
            <FieldError field={field.key} error={validation.errors[field.key]} />
            {"time" in field && (
              <FieldError field={field.time} error={validation.errors[field.time]} />
            )}
          </label>
        ))}
      </div>
      {/* the anchor the other dates run towards; editable only on TOURNAMENT,
          so the field keeps exactly one editor */}
      <p className="rail-hint">
        {t("setup.timeline.anchor", { date: new Date(detail.date).toLocaleDateString("cs") })}
      </p>
      {/* the zone the whole section is read in, set apart from the sequence so
          it does not read as another deadline (spec: setup-navigation) */}
      <label className="form-field timeline-zone">
        <span>
          {t("param.timezone")}
          <HelpHint text={t("setup.timeline.timezoneHint")} />
        </span>
        <select
          value={values.timezone ?? DEFAULT_TIMEZONE}
          onChange={(event) => {
            setValues({ ...values, timezone: event.target.value });
            setDirty(true);
            validation.clearIfValid("timezone", () => null);
          }}
          {...invalidProps("timezone", validation.errors.timezone)}
        >
          {timezoneChoices(values.timezone ?? DEFAULT_TIMEZONE).map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
        <FieldError field="timezone" error={validation.errors.timezone} />
      </label>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
