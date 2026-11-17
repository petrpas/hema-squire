import { useTranslation } from "react-i18next";

import type { Finals, FloorParams } from "../floorApi";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
  wholeNumber,
} from "./shared";

const FINALS: Finals[] = ["elimination", "day", "tournament"];

/** Setup's parameters, each with its kind in words: where the finals go and
 *  the minimum rest (spec floor-setup, Parameters have a default and one
 *  editor). The pool-size preference and the draw weights are the plan's. */
export function ParamsTab({
  slug,
  onSaved,
  onDirty,
  params,
}: SectionProps & { params: FloorParams }) {
  const { t } = useTranslation();
  const [draft, setDraft, dirty] = useDraft(params, "params", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "params", onSaved);
  const errorAt = useErrorText(errors);

  return (
    <SectionCard
      title={t("floor.setup.params.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      <table className="sheet-table floor-params">
        <tbody>
          <tr>
            <th scope="row">{t("floor.setup.params.finals")}</th>
            <td>
              <fieldset className="floor-ticks">
                <legend className="visually-hidden">{t("floor.setup.params.finals")}</legend>
                {FINALS.map((finals) => (
                  <label key={finals}>
                    <input
                      type="radio"
                      name="floor-finals"
                      checked={draft.finals === finals}
                      onChange={() => setDraft({ ...draft, finals })}
                    />
                    {t(`floor.setup.params.finalsAt.${finals}`)}
                  </label>
                ))}
              </fieldset>
            </td>
            <td className="muted">{t("floor.setup.params.kind.rule")}</td>
          </tr>
          <tr>
            <th scope="row">
              <label htmlFor="floor-param-min-rest">
                {t("floor.setup.params.min_rest_minutes")}
              </label>
            </th>
            <td>
              <input
                id="floor-param-min-rest"
                type="number"
                inputMode="numeric"
                min={0}
                max={240}
                value={draft.min_rest_minutes}
                onChange={(event) =>
                  setDraft({ ...draft, min_rest_minutes: wholeNumber(event.target.value) ?? 0 })
                }
              />
              <FieldNote text={errorAt("min_rest_minutes")} />
            </td>
            <td className="muted">{t("floor.setup.params.kind.estimate")}</td>
          </tr>
        </tbody>
      </table>
    </SectionCard>
  );
}
