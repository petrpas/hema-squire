import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { floorApi, type SetupSection } from "../floorApi";

/** Field path → error code, as the server's envelope states them
 *  (`{"detail": {"errors": [{field, code}]}}`). Paths are relative to the
 *  section's body: `0.breaks.1`, `2.name`. */
export type FieldErrors = Record<string, string>;

function fieldErrors(error: unknown): FieldErrors | null {
  if (!(error instanceof ApiError) || error.status !== 422) return null;
  const detail = error.detail;
  if (typeof detail !== "object" || detail === null || !("errors" in detail)) return null;
  const { errors } = detail;
  if (!Array.isArray(errors)) return null;
  const out: FieldErrors = {};
  for (const entry of errors) {
    if (typeof entry === "object" && entry !== null && "field" in entry && "code" in entry) {
      out[String(entry.field)] = String(entry.code);
    }
  }
  return out;
}

/** One section's save: the body goes whole, and a refusal comes back field by
 *  field, nothing stored (spec floor-setup, Floor Setup saves as office Setup
 *  does). */
export function useSectionSave(
  slug: string,
  section: SetupSection,
  onSaved: () => void,
): {
  errors: FieldErrors;
  failed: boolean;
  saving: boolean;
  save: (body: unknown) => Promise<void>;
} {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save(body: unknown) {
    setSaving(true);
    try {
      await floorApi.save(slug, section, body);
      setErrors({});
      setFailed(false);
      onSaved();
    } catch (error) {
      const fields = fieldErrors(error);
      setErrors(fields ?? {});
      setFailed(fields === null);
    } finally {
      setSaving(false);
    }
  }

  return { errors, failed, saving, save };
}

/** The error a field path carries, or one of its children's, as a sentence. */
export function useErrorText(errors: FieldErrors): (path: string) => string | null {
  const { t } = useTranslation();
  return (path: string) => {
    const code = errors[path];
    if (code === undefined) return null;
    return t(`floor.errors.${code}`, { defaultValue: t("floor.errors.invalid") });
  };
}

export function FieldNote({ text }: { text: string | null }) {
  if (text === null) return null;
  return (
    <span className="field-error" role="alert">
      {text}
    </span>
  );
}

/** A Setup section: its title, its body, and its one save control. */
export function SectionCard({
  title,
  hideTitle = false,
  dirty,
  saving,
  failed,
  onSave,
  children,
}: {
  title: string;
  /** the tab's own label already names it: the heading stays for a screen
   *  reader only */
  hideTitle?: boolean;
  dirty: boolean;
  saving: boolean;
  failed: boolean;
  onSave: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card floor-section">
      <h2 className={hideTitle ? "visually-hidden" : undefined}>{title}</h2>
      {children}
      <div className="floor-section-actions">
        {failed && (
          <span className="save-bar-error" role="alert">
            {t("floor.setup.saveFailed")}
          </span>
        )}
        <button type="button" className="btn-primary" disabled={!dirty || saving} onClick={onSave}>
          {saving ? t("floor.setup.saving") : t("floor.setup.save")}
        </button>
      </div>
    </section>
  );
}

/** A date as the organizer reads it: weekday, day and month. */
export function dayLabel(date: string, language: string): string {
  return new Date(`${date}T12:00:00`).toLocaleDateString(language, {
    weekday: "short",
    day: "numeric",
    month: "numeric",
  });
}

/** The weekday's short name, "so" for a Saturday; empty for a date being
 *  typed that does not parse yet. */
export function weekday(date: string, language: string): string {
  const parsed = new Date(`${date}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString(language, { weekday: "short" });
}

/** Ticks for the days of the tournament: one per day, the chosen ones ticked. */
export function DayTicks({
  days,
  chosen,
  onChange,
  label,
}: {
  days: string[];
  chosen: string[];
  onChange: (chosen: string[]) => void;
  label: string;
}) {
  const { i18n } = useTranslation();
  return (
    <fieldset className="floor-ticks">
      <legend className="visually-hidden">{label}</legend>
      {days.map((day) => (
        <label key={day}>
          <input
            type="checkbox"
            checked={chosen.includes(day)}
            onChange={(event) =>
              onChange(
                event.target.checked
                  ? [...chosen, day].sort()
                  : chosen.filter((other) => other !== day),
              )
            }
          />
          {dayLabel(day, i18n.language)}
        </label>
      ))}
    </fieldset>
  );
}

/** What every section is handed. */
export interface SectionProps {
  slug: string;
  onSaved: () => void;
  onDirty: (section: SetupSection, dirty: boolean) => void;
}

/** A section's draft of what the server holds, and whether it differs. The
 *  draft is dropped by remounting the section after a save. */
export function useDraft<T>(
  stored: T,
  section: SetupSection,
  onDirty: SectionProps["onDirty"],
): [T, (next: T) => void, boolean] {
  const [draft, setDraft] = useState<T>(stored);
  const dirty = JSON.stringify(draft) !== JSON.stringify(stored);
  useEffect(() => onDirty(section, dirty), [dirty, section, onDirty]);
  // a section leaving the page holds no unsaved change any more
  useEffect(() => () => onDirty(section, false), [section, onDirty]);
  return [draft, setDraft, dirty];
}

/** A whole number from a field, or null while it reads as none. */
export function wholeNumber(value: string): number | null {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

let nextKey = 0;

function freshKey(): string {
  nextKey += 1;
  return `row-${nextKey}`;
}

/** Client-side identities for a list of rows that has none of its own, kept
 *  in step as rows are added and removed, so a removed row never hands its
 *  field state to the row that slides into its place. */
export function useKeyList(length: number): {
  keys: string[];
  add: () => void;
  remove: (index: number) => void;
} {
  const [keys, setKeys] = useState(() => Array.from({ length }, freshKey));
  return {
    keys,
    add: () => setKeys((current) => [...current, freshKey()]),
    remove: (index) => setKeys((current) => current.filter((_, i) => i !== index)),
  };
}
