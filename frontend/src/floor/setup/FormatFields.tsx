import { useTranslation } from "react-i18next";

import type { FloorDiscipline, FloorFormat, FloorScope } from "../floorApi";
import { NumberField } from "./NumberField";
import { PointsFields } from "./PointsFields";
import { FieldNote, wholeNumber } from "./shared";

/** The fields of one discipline's format (spec floor-setup, Every discipline
 *  has a format). A discipline that takes over asks for no pool fields; the
 *  referees are asked only where they are planned, the lengths only where the
 *  schedule is. */
export function FormatFields({
  format,
  discipline,
  sources,
  scope,
  errorAt,
  onChange,
}: {
  format: FloorFormat;
  discipline: FloorDiscipline;
  /** what it may take over from: the same weapon, not taking over itself */
  sources: FloorDiscipline[];
  scope: FloorScope;
  errorAt: (field: string) => string | null;
  onChange: (format: FloorFormat) => void;
}) {
  const { t } = useTranslation();
  const team = discipline.kind === "team";
  const source = sources.find((d) => d.id === format.takes_pools_from);
  const pools = format.takes_pools_from === null;

  function patch(fields: Partial<FloorFormat>) {
    onChange({ ...format, ...fields });
  }

  function number(
    field: "pool_min" | "pool_max" | "slot_pool_bout" | "slot_elim_bout" | "pause_between_pools",
    min: number,
    max: number,
  ) {
    return (
      <NumberField
        label={t(`floor.setup.formats.${field}`)}
        value={format[field]}
        min={min}
        max={max}
        error={errorAt(field)}
        onChange={(value) => patch({ [field]: value ?? 0 })}
      />
    );
  }

  return (
    <div className="floor-format-fields">
      <fieldset className="floor-wide">
        <legend>{t("floor.setup.formats.pools")}</legend>
        {pools ? (
          <>
            {number("pool_min", 3, 10)}
            {number("pool_max", 3, 10)}
            {team && (
              <p className="muted floor-pools-hint">{t("floor.setup.formats.teamStages")}</p>
            )}
          </>
        ) : (
          <p>{t("floor.setup.formats.takenFrom", { name: source?.name ?? "—" })}</p>
        )}
        {(sources.length > 0 || format.takes_pools_from !== null) && (
          <label>
            {t("floor.setup.formats.takes_pools_from")}
            <select
              value={format.takes_pools_from ?? ""}
              onChange={(event) =>
                patch({
                  takes_pools_from: event.target.value === "" ? null : Number(event.target.value),
                })
              }
            >
              <option value="">{t("floor.setup.formats.ownPools")}</option>
              {sources.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <FieldNote text={errorAt("takes_pools_from")} />
          </label>
        )}
      </fieldset>

      <fieldset className="floor-elimination">
        <legend>
          {t(team ? "floor.setup.formats.teamElimination" : "floor.setup.formats.elimination")}
        </legend>
        <div className="floor-advance">
          <span>{t("floor.setup.formats.advanceLead")}</span>
          <label>
            <input
              type="radio"
              name={`advance-${discipline.id}`}
              checked={format.advance === null}
              onChange={() => patch({ advance: null })}
            />
            {t("floor.setup.formats.advanceAll")}
          </label>
          <label>
            <input
              type="radio"
              name={`advance-${discipline.id}`}
              checked={format.advance !== null}
              onChange={() => patch({ advance: format.advance ?? 16 })}
            />
            {t("floor.setup.formats.advanceFixed")}
          </label>
          <input
            type="number"
            inputMode="numeric"
            aria-label={t("floor.setup.formats.advance")}
            min={2}
            max={999}
            disabled={format.advance === null}
            value={format.advance ?? ""}
            onChange={(event) => patch({ advance: wholeNumber(event.target.value) ?? 0 })}
          />
        </div>
        <FieldNote text={errorAt("advance")} />
        <label className="floor-check">
          <input
            type="checkbox"
            checked={format.third_place}
            onChange={(event) => patch({ third_place: event.target.checked })}
          />
          {t("floor.setup.formats.thirdPlace")}
        </label>
      </fieldset>

      <PointsFields
        format={format}
        team={team}
        teamMin={discipline.team_min}
        pools={pools}
        errorAt={errorAt}
        onChange={patch}
      />

      {scope.plan_officials && (
        <fieldset>
          <legend>{t("floor.setup.formats.referees")}</legend>
          {pools && (
            <NumberField
              label={t("floor.setup.formats.referees_pool")}
              value={format.referees_pool}
              min={1}
              max={9}
              error={errorAt("referees_pool")}
              onChange={(value) => patch({ referees_pool: value ?? 0 })}
            />
          )}
          <NumberField
            label={t("floor.setup.formats.referees_elim")}
            value={format.referees_elim}
            min={1}
            max={9}
            error={errorAt("referees_elim")}
            onChange={(value) => patch({ referees_elim: value ?? 0 })}
          />
        </fieldset>
      )}

      {scope.plan_schedule && (
        <fieldset className="floor-wide">
          <legend>{t("floor.setup.formats.slots")}</legend>
          {pools && number("slot_pool_bout", 1, 600)}
          {team ? (
            <NumberField
              label={t("floor.setup.formats.slot_team_match")}
              value={format.slot_team_match}
              min={1}
              max={600}
              error={errorAt("slot_team_match")}
              onChange={(value) => patch({ slot_team_match: value })}
            />
          ) : (
            number("slot_elim_bout", 1, 600)
          )}
          {pools && number("pause_between_pools", 1, 600)}
        </fieldset>
      )}
    </div>
  );
}
