import { useTranslation } from "react-i18next";

import type { FloorPreferences } from "../floorApi";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
  wholeNumber,
} from "../setup/shared";

const WEIGHTS = ["club_weight", "nationality_weight"] as const;

/** The plan's preferences, with their own save: which pool size the variants
 *  prefer, and the draw's weights (spec floor-plan, The plan's preferences
 *  are edited on the Plan tab). A change orders the next variants; it never
 *  moves the working or published version by itself. */
export function PreferencesSection({
  slug,
  onSaved,
  onDirty,
  preferences,
}: SectionProps & { preferences: FloorPreferences }) {
  const { t } = useTranslation();
  const [draft, setDraft, dirty] = useDraft(preferences, "preferences", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "preferences", onSaved);
  const errorAt = useErrorText(errors);

  return (
    <SectionCard
      title={t("floor.plan.preferences.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      <table className="sheet-table floor-params">
        <tbody>
          <tr>
            <th scope="row">{t("floor.plan.preferences.pool_size")}</th>
            <td>
              <fieldset className="floor-ticks">
                <legend className="visually-hidden">{t("floor.plan.preferences.pool_size")}</legend>
                {(["larger", "smaller"] as const).map((size) => (
                  <label key={size}>
                    <input
                      type="radio"
                      name="floor-pool-size"
                      checked={draft.pool_size === size}
                      onChange={() => setDraft({ ...draft, pool_size: size })}
                    />
                    {t(`floor.plan.preferences.${size}`)}
                  </label>
                ))}
              </fieldset>
            </td>
            <td className="muted">{t("floor.setup.params.kind.preference")}</td>
          </tr>
          {WEIGHTS.map((key) => (
            <tr key={key}>
              <th scope="row">
                <label htmlFor={`floor-pref-${key}`}>{t(`floor.plan.preferences.${key}`)}</label>
              </th>
              <td>
                <input
                  id={`floor-pref-${key}`}
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={100}
                  value={draft[key]}
                  onChange={(event) =>
                    setDraft({ ...draft, [key]: wholeNumber(event.target.value) ?? 0 })
                  }
                />
                <FieldNote text={errorAt(key)} />
              </td>
              <td className="muted">{t("floor.setup.params.kind.preference")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionCard>
  );
}
