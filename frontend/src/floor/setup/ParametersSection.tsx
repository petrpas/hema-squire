import { useTranslation } from "react-i18next";

import type { FloorParams } from "../floorApi";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
  wholeNumber,
} from "./shared";

type Kind = "rule" | "preference" | "estimate";

const FLAGS: { key: "finals_last" | "prefer_larger_pools"; kind: Kind }[] = [
  { key: "finals_last", kind: "rule" },
  { key: "prefer_larger_pools", kind: "preference" },
];

const NUMBERS: {
  key: "club_weight" | "nationality_weight" | "min_rest_minutes";
  kind: Kind;
  max: number;
}[] = [
  { key: "club_weight", kind: "preference", max: 100 },
  { key: "nationality_weight", kind: "preference", max: 100 },
  { key: "min_rest_minutes", kind: "estimate", max: 240 },
];

/** The organizer's parameters, each with its kind stated in words, edited
 *  here and in no step of the console (spec floor-setup, Parameters have a
 *  default and one editor). */
export function ParametersSection({
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
            <th scope="row">{t("floor.setup.params.pool_sizes_even")}</th>
            <td>{t("floor.setup.params.always")}</td>
            <td className="muted">{t("floor.setup.params.kind.rule")}</td>
          </tr>
          {FLAGS.map(({ key, kind }) => (
            <tr key={key}>
              <th scope="row">
                <label htmlFor={`floor-param-${key}`}>{t(`floor.setup.params.${key}`)}</label>
              </th>
              <td>
                <input
                  id={`floor-param-${key}`}
                  type="checkbox"
                  checked={draft[key]}
                  onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })}
                />
              </td>
              <td className="muted">{t(`floor.setup.params.kind.${kind}`)}</td>
            </tr>
          ))}
          {NUMBERS.map(({ key, kind, max }) => (
            <tr key={key}>
              <th scope="row">
                <label htmlFor={`floor-param-${key}`}>{t(`floor.setup.params.${key}`)}</label>
              </th>
              <td>
                <input
                  id={`floor-param-${key}`}
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={max}
                  value={draft[key]}
                  onChange={(event) =>
                    setDraft({ ...draft, [key]: wholeNumber(event.target.value) ?? 0 })
                  }
                />
                <FieldNote text={errorAt(key)} />
              </td>
              <td className="muted">{t(`floor.setup.params.kind.${kind}`)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionCard>
  );
}
