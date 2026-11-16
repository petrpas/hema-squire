import { useTranslation } from "react-i18next";

import type { FloorFormat, Staffing } from "../floorApi";
import { FieldNote, wholeNumber } from "./shared";

const ROLES = ["referee", "judge", "table"] as const;

/** The fields of one discipline's format. */
export function FormatFields({
  format,
  team,
  errorAt,
  onChange,
}: {
  format: FloorFormat;
  team: boolean;
  errorAt: (field: string) => string | null;
  onChange: (format: FloorFormat) => void;
}) {
  const { t } = useTranslation();

  function patch(fields: Partial<FloorFormat>) {
    onChange({ ...format, ...fields });
  }

  function number(
    field: "pool_min" | "pool_max" | "slot_pool_bout" | "slot_elim_bout" | "slot_pool_overhead",
    min: number,
    max: number,
  ) {
    return (
      <label>
        {t(`floor.setup.formats.${field}`)}
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          value={format[field]}
          onChange={(event) => patch({ [field]: wholeNumber(event.target.value) ?? 0 })}
        />
        <FieldNote text={errorAt(field)} />
      </label>
    );
  }

  function staff(role: keyof Staffing, value: string) {
    const current = format.staffing ?? { referee: 0, judge: 0, table: 0 };
    patch({ staffing: { ...current, [role]: wholeNumber(value) ?? 0 } });
  }

  return (
    <div className="floor-format-fields">
      <fieldset>
        <legend>{t("floor.setup.formats.pools")}</legend>
        {number("pool_min", 3, 10)}
        {number("pool_max", 3, 10)}
      </fieldset>

      <fieldset>
        <legend>{t("floor.setup.formats.elimination")}</legend>
        {team && <p className="muted">{t("floor.setup.formats.teamStages")}</p>}
        <label className="floor-check">
          <input
            type="checkbox"
            checked={format.advance === null}
            onChange={(event) => patch({ advance: event.target.checked ? null : 16 })}
          />
          {t("floor.setup.formats.advanceAll")}
        </label>
        {format.advance !== null && (
          <label>
            {t("floor.setup.formats.advance")}
            <input
              type="number"
              inputMode="numeric"
              min={2}
              value={format.advance}
              onChange={(event) => patch({ advance: wholeNumber(event.target.value) ?? 0 })}
            />
          </label>
        )}
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

      <fieldset>
        <legend>{t("floor.setup.formats.staffing")}</legend>
        {format.staffing === null ? (
          <button
            type="button"
            className="secondary"
            onClick={() => patch({ staffing: { referee: 1, judge: 0, table: 0 } })}
          >
            {t("floor.setup.formats.stateStaffing")}
          </button>
        ) : (
          ROLES.map((role) => (
            <label key={role}>
              {t(`floor.roles.${role}`)}
              <input
                type="number"
                inputMode="numeric"
                min={role === "referee" ? 1 : 0}
                max={9}
                value={format.staffing?.[role] ?? 0}
                onChange={(event) => staff(role, event.target.value)}
              />
              <FieldNote text={errorAt(`staffing.${role}`)} />
            </label>
          ))
        )}
      </fieldset>

      <fieldset>
        <legend>{t("floor.setup.formats.slots")}</legend>
        {number("slot_pool_bout", 1, 600)}
        {number("slot_elim_bout", 1, 600)}
        {number("slot_pool_overhead", 1, 600)}
        {team && (
          <label>
            {t("floor.setup.formats.slot_team_match")}
            <input
              type="number"
              inputMode="numeric"
              min={1}
              value={format.slot_team_match ?? ""}
              onChange={(event) => patch({ slot_team_match: wholeNumber(event.target.value) })}
            />
            <FieldNote text={errorAt("slot_team_match")} />
          </label>
        )}
      </fieldset>
    </div>
  );
}
