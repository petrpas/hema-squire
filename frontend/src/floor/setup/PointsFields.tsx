import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { FloorFormat } from "../floorApi";
import { FieldNote, wholeNumber } from "./shared";

/** A team match's total: points per bout times k² bouts, k the discipline's
 *  minimum team size (owner decision 2026-11-17). */
export function teamTotal(points: number, teamMin: number | null | undefined): number {
  const k = teamMin ?? 3;
  return points * k * k;
}

/** A format's point targets, each optional: the pool bout, and either an
 *  individual elimination bout or a team discipline's points per bout with
 *  the match total (spec floor-setup, Every discipline has a format). */
export function PointsFields({
  format,
  team,
  teamMin,
  pools,
  errorAt,
  onChange,
}: {
  format: FloorFormat;
  team: boolean;
  teamMin: number | null | undefined;
  /** false for a discipline that takes over: it fences no pools */
  pools: boolean;
  errorAt: (field: string) => string | null;
  onChange: (fields: Partial<FloorFormat>) => void;
}) {
  const { t } = useTranslation();
  const perBout = format.points_team_bout;

  return (
    <fieldset className="floor-points">
      <legend>{t("floor.setup.formats.points")}</legend>
      {pools && (
        <PointRow
          label={t("floor.setup.formats.points_pool")}
          value={format.points_pool}
          error={errorAt("points_pool")}
          onChange={(value) => onChange({ points_pool: value })}
        />
      )}
      {team ? (
        <PointRow
          label={t("floor.setup.formats.points_team_bout")}
          value={perBout}
          error={errorAt("points_team_bout")}
          onChange={(value) => onChange({ points_team_bout: value })}
          after={
            perBout !== null &&
            t("floor.setup.formats.teamTotal", { total: teamTotal(perBout, teamMin) })
          }
        />
      ) : (
        <PointRow
          label={t("floor.setup.formats.points_elim")}
          value={format.points_elim}
          error={errorAt("points_elim")}
          onChange={(value) => onChange({ points_elim: value })}
        />
      )}
    </fieldset>
  );
}

/** One target as a row: the label, the field, and what follows from it. */
function PointRow({
  label,
  value,
  error,
  after,
  onChange,
}: {
  label: string;
  value: number | null;
  error: string | null;
  after?: ReactNode;
  onChange: (value: number | null) => void;
}) {
  return (
    <>
      <label className="floor-points-row">
        <span>{label}</span>
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={99}
          value={value ?? ""}
          onChange={(event) => onChange(wholeNumber(event.target.value))}
        />
        {after && <span>{after}</span>}
      </label>
      <FieldNote text={error} />
    </>
  );
}
