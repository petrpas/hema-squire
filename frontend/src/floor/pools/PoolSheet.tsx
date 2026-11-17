import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { type DrawPool, type Outcome, type PoolBout, poolsApi, type ResultIn } from "../floorApi";

type Draft = { a: string; b: string; none: boolean; note: string };

function draftOf(bout: PoolBout): Draft {
  return {
    a: bout.score_a === null ? "" : String(bout.score_a),
    b: bout.score_b === null ? "" : String(bout.score_b),
    none: bout.outcome_a === "no",
    note: bout.note ?? "",
  };
}

/** The adopted model's outcomes from the scores: the higher wins, equal is a
 *  draw; "no bout" is stated on its own. */
function resultOf(draft: Draft, version: number): ResultIn | null {
  const a = Number.parseInt(draft.a, 10);
  const b = Number.parseInt(draft.b, 10);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  const outcomes: [Outcome, Outcome] = draft.none
    ? ["no", "no"]
    : a > b
      ? ["win", "loss"]
      : a < b
        ? ["loss", "win"]
        : ["draw", "draw"];
  return {
    score_a: a,
    score_b: b,
    outcome_a: outcomes[0],
    outcome_b: outcomes[1],
    note: draft.note.trim() || null,
    version,
  };
}

/** One pool's bouts in sheet order: each recorded on its own, or the whole
 *  paper sheet saved at once (spec floor-pools, Bouts are recorded by the
 *  adopted model). */
export function PoolSheet({
  slug,
  discipline,
  pool,
  name,
  locked,
  onChanged,
}: {
  slug: string;
  discipline: number;
  pool: DrawPool;
  name: (key: string) => string;
  locked: boolean;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [refusal, setRefusal] = useState<string | null>(null);

  const draft = (bout: PoolBout) => drafts[bout.id] ?? draftOf(bout);
  const edit = (bout: PoolBout, fields: Partial<Draft>) =>
    setDrafts({ ...drafts, [bout.id]: { ...draft(bout), ...fields } });

  async function save(action: () => Promise<unknown>, ids: number[]) {
    setRefusal(null);
    try {
      await action();
      const rest = { ...drafts };
      for (const id of ids) delete rest[id];
      setDrafts(rest);
    } catch (error) {
      setRefusal(
        error instanceof ApiError && typeof error.detail === "string" ? error.detail : "failed",
      );
    }
    onChanged();
  }

  const pending = pool.bouts.filter((b) => drafts[b.id] !== undefined);

  return (
    <article className="floor-pool">
      <table className="sheet-table floor-bouts">
        <tbody>
          {pool.bouts.map((bout) => {
            const current = draft(bout);
            const result = resultOf(current, bout.version);
            return (
              <tr key={bout.id} className={bout.score_a === null ? "" : "floor-recorded"}>
                <td>{bout.ordinal}.</td>
                <th scope="row">{name(bout.a)}</th>
                <td>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={99}
                    aria-label={t("floor.pools.scoreOf", { name: name(bout.a) })}
                    value={current.a}
                    disabled={locked}
                    onChange={(event) => edit(bout, { a: event.target.value })}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={99}
                    aria-label={t("floor.pools.scoreOf", { name: name(bout.b) })}
                    value={current.b}
                    disabled={locked}
                    onChange={(event) => edit(bout, { b: event.target.value })}
                  />
                </td>
                <th scope="row">{name(bout.b)}</th>
                <td>
                  <label className="floor-check">
                    <input
                      type="checkbox"
                      checked={current.none}
                      disabled={locked}
                      onChange={(event) => edit(bout, { none: event.target.checked })}
                    />
                    {t("floor.pools.noBout")}
                  </label>
                </td>
                <td>
                  {!locked && drafts[bout.id] !== undefined && (
                    <button
                      type="button"
                      className="secondary"
                      disabled={result === null}
                      onClick={() =>
                        result !== null &&
                        void save(() => poolsApi.record(slug, bout.id, result), [bout.id])
                      }
                    >
                      {t("floor.setup.save")}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!locked && pending.length > 1 && (
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            const bouts = pending.flatMap((b) => {
              const result = resultOf(draft(b), b.version);
              return result === null ? [] : [{ ...result, id: b.id }];
            });
            void save(
              () => poolsApi.transcribe(slug, discipline, bouts),
              bouts.map((b) => b.id),
            );
          }}
        >
          {t("floor.pools.saveSheet", { count: pending.length })}
        </button>
      )}
      {refusal !== null && (
        <p className="floor-missing" role="alert">
          {t(`floor.pools.refusals.${refusal}`, { defaultValue: t("floor.plan.failed") })}
        </p>
      )}
    </article>
  );
}
