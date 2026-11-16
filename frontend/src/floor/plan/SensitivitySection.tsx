import { useTranslation } from "react-i18next";

import type { Sensitivity } from "../floorApi";

/** Sensitivity of the chosen variant: where a discipline's pools would
 *  change, and what one piste more or fewer would do to each day (spec
 *  floor-planner, Sensitivity is reported with the chosen variant). */
export function SensitivitySection({
  sensitivity,
  names,
}: {
  sensitivity: Sensitivity;
  names: Map<number, string>;
}) {
  const { t } = useTranslation();
  const shift = (minutes: number | null) =>
    minutes === null
      ? t("floor.plan.sensitivity.unplannable")
      : minutes === 0
        ? t("floor.plan.sensitivity.nothing")
        : t(minutes < 0 ? "floor.plan.sensitivity.earlier" : "floor.plan.sensitivity.later", {
            count: Math.abs(minutes),
          });

  return (
    <section className="rail-card">
      <h2>{t("floor.plan.sensitivity.title")}</h2>
      <ul>
        {sensitivity.thresholds.map((threshold) => (
          <li key={threshold.discipline_id}>
            {t("floor.plan.sensitivity.threshold", {
              name: names.get(threshold.discipline_id) ?? threshold.discipline_id,
              below: threshold.below ?? "—",
              above: threshold.above ?? "—",
            })}
          </li>
        ))}
      </ul>
      <ul>
        {sensitivity.days.map((effect) => (
          <li key={effect.day}>
            {effect.day}: {t("floor.plan.sensitivity.fewer")} {shift(effect.one_fewer)};{" "}
            {t("floor.plan.sensitivity.more")} {shift(effect.one_more)};{" "}
            {t("floor.plan.sensitivity.twoMore")} {shift(effect.two_more)}.{" "}
            {effect.limit !== "none" && t(`floor.plan.sensitivity.limit.${effect.limit}`)}
          </li>
        ))}
      </ul>
    </section>
  );
}
