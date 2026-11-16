import { useTranslation } from "react-i18next";

import type { Infeasible } from "../floorApi";

/** Why there is no variant, in one of four messages that are never merged:
 *  a structure, a pin, a rule, an overrun (spec floor-planner, Explaining an
 *  empty result). */
export function InfeasibleText({
  infeasible,
  names,
}: {
  infeasible: Infeasible;
  names: Map<number, string>;
}) {
  const { t } = useTranslation();
  const { reason, subject } = infeasible;
  let text: string;
  if (reason === "structure") {
    text = t("floor.plan.infeasible.structure", {
      name: typeof subject === "string" ? (names.get(Number(subject)) ?? subject) : "",
      detail: infeasible.detail,
    });
  } else if (reason === "pin" && typeof subject !== "string") {
    const name = names.get(Number(subject.target)) ?? subject.target;
    text = t(`floor.plan.infeasible.pin.${subject.kind}`, {
      name,
      day: subject.day ?? "",
      k: subject.k ?? "",
      defaultValue: t("floor.plan.infeasible.pin.other", { name }),
    });
  } else if (reason === "rule") {
    text = t("floor.plan.infeasible.rule", {
      rule: t(`floor.plan.rules.${typeof subject === "string" ? subject : ""}`),
    });
  } else {
    text = t("floor.plan.infeasible.overrun", { minutes: infeasible.minutes });
  }
  return (
    <p className="floor-missing" role="status">
      {text}
    </p>
  );
}
