import { useTranslation } from "react-i18next";

import type { FloorDiscipline, FloorFormat, FloorFormatOut, FloorScope } from "../floorApi";
import { FormatFields } from "./FormatFields";
import { SectionCard, type SectionProps, useDraft, useErrorText, useSectionSave } from "./shared";

/** A weapon as the floor compares it: case-folded (spec floor-roster). */
function weaponOf(discipline: FloorDiscipline): string {
  return (discipline.weapon ?? "").trim().toLowerCase();
}

/** One format per discipline (spec floor-setup, Every discipline has a
 *  format). A format never saved is offered with its defaults. The whole set
 *  is saved together. */
export function FormatsTab({
  slug,
  onSaved,
  onDirty,
  formats,
  disciplines,
  scope,
}: SectionProps & {
  formats: FloorFormatOut[];
  disciplines: FloorDiscipline[];
  scope: FloorScope;
}) {
  const { t } = useTranslation();
  const stored = formats.map(({ stored: _s, missing: _m, ...format }) => format);
  const [draft, setDraft, changed] = useDraft<FloorFormat[]>(stored, "formats", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "formats", onSaved);
  const errorAt = useErrorText(errors);
  const unsaved = formats.some((format) => !format.stored);

  /** What a discipline may take its pool results over from, in the draft. */
  function sources(discipline: FloorDiscipline): FloorDiscipline[] {
    return disciplines.filter((other) => {
      if (other.id === discipline.id || weaponOf(other) !== weaponOf(discipline)) return false;
      const theirs = draft.find((f) => f.discipline_id === other.id);
      return theirs === undefined || theirs.takes_pools_from === null;
    });
  }

  return (
    <SectionCard
      title={t("floor.setup.formats.title")}
      hideTitle
      dirty={changed || unsaved}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      {draft.map((format, index) => {
        const discipline = disciplines.find((d) => d.id === format.discipline_id);
        const out = formats[index];
        if (discipline === undefined || out === undefined) return null;
        return (
          <div key={format.discipline_id} className="floor-format">
            <h3>{discipline.name}</h3>
            {out.missing.length > 0 && (
              <p className="floor-missing">
                {out.missing.map((what) => t(`floor.setup.formats.missing.${what}`)).join(" ")}
              </p>
            )}
            <FormatFields
              format={format}
              discipline={discipline}
              sources={sources(discipline)}
              scope={scope}
              errorAt={(field) => errorAt(`${index}.${field}`)}
              onChange={(next) => setDraft(draft.map((f, i) => (i === index ? next : f)))}
            />
          </div>
        );
      })}
    </SectionCard>
  );
}
