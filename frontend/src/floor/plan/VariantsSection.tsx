import { useState } from "react";
import { useTranslation } from "react-i18next";

import { planApi, type Variant, type Variants } from "../floorApi";
import { InfeasibleText } from "./InfeasibleText";

/** The planner's variants side by side: per discipline k, pool sizes and
 *  day; per day the last end; the exclusion load and the collisions. The
 *  first is the default. Choosing one makes it the working version. */
export function VariantsSection({
  slug,
  names,
  onChosen,
}: {
  slug: string;
  names: Map<number, string>;
  onChosen: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [found, setFound] = useState<Variants | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function ask() {
    setBusy(true);
    setFailed(false);
    try {
      setFound(await planApi.variants(slug));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  async function choose(variant: Variant) {
    setBusy(true);
    try {
      await planApi.choose(slug, variant.key);
      onChosen();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const dayLabel = (day: string) =>
    new Date(`${day}T12:00:00`).toLocaleDateString(i18n.language, {
      weekday: "short",
      day: "numeric",
      month: "numeric",
    });

  return (
    <section className="rail-card">
      <h2>{t("floor.plan.variants.title")}</h2>
      <button type="button" className="btn-primary" disabled={busy} onClick={() => void ask()}>
        {busy ? t("floor.plan.variants.working") : t("floor.plan.variants.ask")}
      </button>
      {failed && (
        <p className="save-bar-error" role="alert">
          {t("floor.plan.failed")}
        </p>
      )}
      {found !== null && found.infeasible !== null && (
        <InfeasibleText infeasible={found.infeasible} names={names} />
      )}
      {found !== null && found.empty.length > 0 && (
        <p className="muted">
          {t("floor.plan.variants.empty", {
            names: found.empty.map((id) => names.get(id) ?? id).join(", "),
          })}
        </p>
      )}
      {found !== null && found.capped.length > 0 && (
        <p className="muted">
          {t("floor.plan.variants.capped", {
            names: found.capped.map((id) => names.get(id) ?? id).join(", "),
          })}
        </p>
      )}
      {found !== null && found.variants.length > 0 && (
        <div className="floor-variants">
          {found.variants.map((variant, index) => (
            <article key={variant.key} className="floor-variant">
              <h3>
                {t("floor.plan.variants.number", { number: index + 1 })}
                {index === 0 && <span className="muted"> {t("floor.plan.variants.default")}</span>}
              </h3>
              <ul>
                {variant.choices.map((choice) => (
                  <li key={choice.discipline_id}>
                    {names.get(choice.discipline_id)}:{" "}
                    {choice.k === 0
                      ? t("floor.plan.variants.takenOver")
                      : t("floor.plan.variants.pools", {
                          count: choice.k,
                          sizes: [...new Set(choice.sizes)].join("/"),
                        })}
                    {choice.day !== null && `, ${dayLabel(choice.day)}`}
                  </li>
                ))}
              </ul>
              <ul className="muted">
                {Object.entries(variant.metrics.last_end).map(([day, end]) => (
                  <li key={day}>{t("floor.plan.variants.ends", { day: dayLabel(day), end })}</li>
                ))}
                {/* a plan without a schedule has no times, waves or collisions */}
                {variant.activities.length > 0 && (
                  <>
                    <li>
                      {t("floor.plan.variants.load", { count: variant.metrics.exclusion_load })}
                    </li>
                    <li>
                      {t("floor.plan.variants.collisions", { count: variant.metrics.collisions })}
                    </li>
                  </>
                )}
                {variant.metrics.shortage > 0 && (
                  <li>{t("floor.plan.variants.shortage", { count: variant.metrics.shortage })}</li>
                )}
                {(variant.metrics.reserve_used ?? []).length > 0 && (
                  <li>
                    {t("floor.plan.variants.reserveUsed", {
                      count: (variant.metrics.reserve_used ?? []).length,
                    })}
                  </li>
                )}
                {(variant.metrics.main_warnings ?? []).map((warning) => (
                  <li key={`${warning.day}-${warning.at}`}>
                    {t("floor.plan.variants.mainShort", {
                      day: dayLabel(warning.day),
                      at: warning.at,
                      count: warning.short,
                    })}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => void choose(variant)}
              >
                {t("floor.plan.variants.choose")}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
