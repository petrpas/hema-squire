import { useState } from "react";
import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import { type FloorPiste, type PlanState, planApi } from "../floorApi";

/** The working version and its difference against the published one, in
 *  the work (spec floor-plan, The working plan is compared with the
 *  published one). */
export function WorkingDiff({ plan, pistes }: { plan: PlanState; pistes: FloorPiste[] }) {
  const { t } = useTranslation();
  const pisteName = new Map(pistes.map((p) => [p.id, p.name]));
  const where = (place: [number, string, string] | null) =>
    place === null ? "—" : `${pisteName.get(place[0]) ?? place[0]}, ${place[2]}`;

  return (
    <section className="rail-card">
      <h2>{t("floor.plan.working.title")}</h2>
      {plan.published && (
        <p className="muted">
          {t("floor.plan.working.published", { version: plan.published.version })}
        </p>
      )}
      {plan.working === null ? (
        <p className="muted">{t("floor.plan.working.none")}</p>
      ) : (
        <>
          <p>{t("floor.plan.working.version", { version: plan.working.version })}</p>
          {plan.diff.length > 0 && (
            <ul className="floor-diff">
              {plan.diff.map((change) => (
                <li key={change.activity}>
                  <strong>{change.activity}</strong> {t(`floor.schedule.change.${change.kind}`)}
                  {change.kind === "moved" && `: ${where(change.before)} → ${where(change.after)}`}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

/** The publish gate with its obstacles, and re-planning, which is only ever
 *  asked for: the Plan tab's operations (spec floor-plan). */
export function PublishGate({
  slug,
  plan,
  names,
  onChanged,
}: {
  slug: string;
  plan: PlanState;
  names: Map<number, string>;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  function obstacle(code: string): string {
    const [kind, a = "", b = ""] = code.split(":");
    if (kind === "format")
      return t("floor.plan.obstacles.format", { name: names.get(Number(a)) ?? a });
    if (kind === "no_piste") return t("floor.plan.obstacles.noPiste", { day: a });
    if (kind === "shortage") {
      return t("floor.plan.obstacles.shortage", {
        a: names.get(Number(a)) ?? a,
        b: names.get(Number(b)) ?? b,
      });
    }
    return code;
  }

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setFailed(false);
    try {
      await action();
      onChanged();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  if (plan.working === null && !plan.published) return null;

  return (
    <section className="rail-card">
      <h2>{t("floor.plan.working.publish")}</h2>
      {plan.working === null ? (
        <p className="rail-hint">{t("floor.plan.working.none")}</p>
      ) : (
        <>
          {plan.obstacles.length > 0 && (
            <ul className="floor-obstacles">
              {plan.obstacles.map((code) => (
                <li key={code} className="floor-missing">
                  {obstacle(code)}
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            className="btn-primary"
            disabled={busy || plan.obstacles.length > 0}
            onClick={() => setConfirming(true)}
          >
            {t("floor.plan.working.publish")}
          </button>
        </>
      )}
      {plan.published && (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => void act(() => planApi.replan(slug))}
        >
          {t("floor.plan.working.replan")}
        </button>
      )}
      {failed && (
        <p className="save-bar-error" role="alert">
          {t("floor.plan.failed")}
        </p>
      )}
      {confirming && (
        <Modal onClose={() => setConfirming(false)}>
          <div className="modal">
            <h2>{t("floor.plan.working.confirmTitle")}</h2>
            <p>{t("floor.plan.working.confirmBody")}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() => void act(() => planApi.publish(slug))}
              >
                {t("floor.plan.working.publish")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
