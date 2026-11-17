import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { type Assignments, type FloorSetup, officialsApi } from "../floorApi";
import { openPdf } from "../pdf";

/** Obsazení: blocks × roles with names, empty seats, club conflicts and pins
 *  whose block is gone; a seat is set (and pinned) here, refused with the
 *  broken rule named; each official's rozpis and each piste's sheet print
 *  (spec floor-officials). */
export function AssignmentSection({ slug, setup }: { slug: string; setup: FloorSetup }) {
  const { t } = useTranslation();
  const [data, setData] = useState<Assignments | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);

  const load = useCallback(() => {
    officialsApi.view(slug).then(setData, () => setData(null));
  }, [slug]);
  useEffect(load, [load]);

  if (data === null || !data.published) return null;
  const names = new Map(setup.disciplines.map((d) => [d.id, d.name]));
  const pistes = new Map(setup.pistes.map((p) => [p.id ?? 0, p.name]));

  async function set(seat: number, official: number | null, pinned: boolean) {
    setRefusal(null);
    try {
      await officialsApi.seat(slug, seat, official, pinned);
    } catch (error) {
      setRefusal(
        error instanceof ApiError && typeof error.detail === "string" ? error.detail : "failed",
      );
    }
    load();
  }

  return (
    <section className="rail-card">
      <h2>
        {t("floor.officials.title")}{" "}
        <button
          type="button"
          className="secondary"
          onClick={() => void officialsApi.run(slug).then(load)}
        >
          {t("floor.officials.rerun")}
        </button>
      </h2>
      {refusal !== null && (
        <p className="floor-missing" role="alert">
          {t(`floor.officials.rules.${refusal}`, { defaultValue: t("floor.plan.failed") })}
        </p>
      )}
      {data.conflicts.length > 0 && (
        <ul className="floor-obstacles">
          {data.conflicts.map((c) => (
            <li key={`${c.block}-${c.official_id}`} className="floor-missing">
              {t("floor.officials.conflict", {
                name: setup.officials.find((o) => o.id === c.official_id)?.name ?? c.official_id,
                club: c.club,
              })}
            </li>
          ))}
        </ul>
      )}
      {data.unmatched.length > 0 && (
        <p className="floor-missing">
          {t("floor.officials.unmatched", { count: data.unmatched.length })}
        </p>
      )}
      <table className="sheet-table floor-assignments">
        <tbody>
          {data.blocks.map((block) => (
            <tr key={block.key}>
              <th scope="row">
                {block.start}–{block.end} · {pistes.get(block.piste_id) ?? block.piste_id} ·{" "}
                {names.get(block.discipline_id)}
              </th>
              {block.seats.map((seat) => (
                <td key={seat.id}>
                  <label>
                    <span className="muted">{t(`floor.roles.${seat.role}`)}</span>
                    <select
                      value={seat.official_id ?? ""}
                      onChange={(event) =>
                        void set(
                          seat.id,
                          event.target.value === "" ? null : Number(event.target.value),
                          true,
                        )
                      }
                    >
                      <option value="">{t("floor.officials.empty")}</option>
                      {setup.officials.map((o) => (
                        <option key={o.id ?? o.name} value={o.id ?? ""}>
                          {o.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {seat.pinned && <span className="muted"> {t("floor.officials.pinned")}</span>}
                  {seat.official_id === null && (
                    <span className="floor-missing"> {t("floor.officials.unfilled")}</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="floor-row-actions">
        <span>{t("floor.officials.print")}</span>
        {setup.officials.map((o) =>
          o.id === null ? null : (
            <button
              key={o.id}
              type="button"
              className="secondary"
              onClick={() => void openPdf(officialsApi.printUrl(slug, "official", o.id ?? 0))}
            >
              {o.name}
            </button>
          ),
        )}
        {setup.pistes.map((p) =>
          p.id === null ? null : (
            <button
              key={`p-${p.id}`}
              type="button"
              className="secondary"
              onClick={() => void openPdf(officialsApi.printUrl(slug, "piste", p.id ?? 0))}
            >
              {t("floor.ring.piste", { name: p.name })}
            </button>
          ),
        )}
      </div>
    </section>
  );
}
