import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import Modal from "../../Modal";
import { type CloseImpact, checkinApi, type DeskDiscipline } from "../floorApi";

type Dialog =
  | { kind: "close"; impact: CloseImpact }
  | { kind: "reopen"; invalidated: string[]; refusals: string[] };

/** A discipline's check-in: its counts, and the gate that closes it, its
 *  impact stated before confirming, or reopens it with what that discards
 *  (spec floor-checkin). */
export function DisciplineGate({
  slug,
  discipline,
  onChanged,
}: {
  slug: string;
  discipline: DeskDiscipline;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [refused, setRefused] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);

  async function open() {
    setFailed(false);
    try {
      if (discipline.closed) {
        const preview = await checkinApi.reopenPreview(slug, discipline.id);
        setDialog({ kind: "reopen", ...preview });
      } else {
        setDialog({ kind: "close", impact: await checkinApi.impact(slug, discipline.id) });
      }
    } catch {
      setFailed(true);
    }
  }

  async function confirm() {
    if (dialog === null) return;
    try {
      if (dialog.kind === "close") await checkinApi.close(slug, discipline.id);
      else await checkinApi.reopen(slug, discipline.id);
      setDialog(null);
      onChanged();
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      if (
        typeof detail === "object" &&
        detail !== null &&
        "items" in detail &&
        Array.isArray(detail.items)
      ) {
        setRefused(detail.items.map(String));
      } else {
        setFailed(true);
      }
      setDialog(null);
    }
  }

  function impactText(impact: CloseImpact): string {
    if (!impact.feasible) {
      return t("floor.checkin.impact.infeasible", {
        n: impact.n,
        range: impact.range?.join("–") ?? "",
      });
    }
    const pools =
      impact.published_k !== null && impact.published_k !== impact.k
        ? t("floor.checkin.impact.poolsInstead", { k: impact.k, was: impact.published_k })
        : t("floor.checkin.impact.pools", {
            k: impact.k,
            sizes: [...new Set(impact.sizes)].join("/"),
          });
    const end =
      impact.end_change === null || impact.end_change === 0
        ? ""
        : `, ${t(impact.end_change < 0 ? "floor.checkin.impact.earlier" : "floor.checkin.impact.later", { count: Math.abs(impact.end_change) })}`;
    return `N = ${impact.n}, ${pools}${end}`;
  }

  return (
    <section className="rail-card floor-gate">
      <h2>{discipline.name}</h2>
      <p>
        {discipline.closed
          ? t("floor.checkin.closedAt", { n: discipline.n ?? 0 })
          : t("floor.checkin.counts", { present: discipline.present, entered: discipline.entered })}
      </p>
      <button type="button" className="secondary" onClick={() => void open()}>
        {discipline.closed ? t("floor.checkin.reopen") : t("floor.checkin.close")}
      </button>
      {failed && (
        <p className="save-bar-error" role="alert">
          {t("floor.plan.failed")}
        </p>
      )}
      {refused !== null && (
        <p className="floor-missing" role="alert">
          {t("floor.checkin.reopenRefused", { items: refused.join(", ") })}
        </p>
      )}
      {dialog !== null && (
        <Modal onClose={() => setDialog(null)}>
          <div className="modal">
            <h2>
              {dialog.kind === "close"
                ? t("floor.checkin.closeTitle", { name: discipline.name })
                : t("floor.checkin.reopenTitle", { name: discipline.name })}
            </h2>
            {dialog.kind === "close" ? (
              <p>{impactText(dialog.impact)}</p>
            ) : (
              <>
                <p>{t("floor.checkin.invalidates")}</p>
                <ul>
                  {dialog.invalidated.map((code) => (
                    <li key={code}>
                      {t(`floor.checkin.invalidated.${code}`, { defaultValue: code })}
                    </li>
                  ))}
                </ul>
                {dialog.refusals.length > 0 && (
                  <p className="floor-missing">
                    {t("floor.checkin.reopenRefused", { items: dialog.refusals.join(", ") })}
                  </p>
                )}
              </>
            )}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setDialog(null)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={dialog.kind === "reopen" && dialog.refusals.length > 0}
                onClick={() => void confirm()}
              >
                {dialog.kind === "close" ? t("floor.checkin.close") : t("floor.checkin.reopen")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
