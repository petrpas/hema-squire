import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { getToken } from "../../api";
import { type DisciplineResults, resultsApi } from "../floorApi";
import { openPdf } from "../pdf";

/** Saves the CSV export, fetched with the console's credential. */
async function download(url: string, name: string) {
  const token = getToken();
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) return;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(await response.blob());
  link.download = name;
  link.click();
}

/** Výsledky: each discipline's final standing once its bracket closes, its
 *  export and print, and the publish gate (spec floor-results). */
export default function ResultsTab({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [data, setData] = useState<DisciplineResults[] | null>(null);

  const load = useCallback(() => {
    resultsApi.list(slug).then(setData, () => setData([]));
  }, [slug]);
  useEffect(load, [load]);

  if (data === null) return <p>{t("common.loading")}</p>;

  return (
    <div className="floor-data">
      {data.map((row) => (
        <section key={row.discipline_id} className="rail-card">
          <h2>
            {row.name}{" "}
            <span className="muted">
              {row.published_at ? t("floor.results.published") : t("floor.results.waiting")}
            </span>
          </h2>
          {row.standing === null ? (
            <p className="muted">{t("floor.results.bracketOpen")}</p>
          ) : (
            <>
              <table className="sheet-table">
                <thead>
                  <tr>
                    <th scope="col">{t("floor.results.place")}</th>
                    <th scope="col">{t("floor.data.name")}</th>
                    <th scope="col">{t("floor.data.club")}</th>
                    <th scope="col">{t("floor.data.nationality")}</th>
                  </tr>
                </thead>
                <tbody>
                  {row.standing.map((r) => (
                    <tr key={r.key ?? r.name}>
                      <td>{r.place}.</td>
                      <th scope="row">{r.name}</th>
                      <td>{r.club}</td>
                      <td>{r.nationality}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="floor-row-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    void download(
                      resultsApi.exportUrl(slug, row.discipline_id, "csv"),
                      `${row.slug}.csv`,
                    )
                  }
                >
                  {t("floor.results.csv")}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void openPdf(resultsApi.exportUrl(slug, row.discipline_id, "pdf"))}
                >
                  {t("floor.results.print")}
                </button>
                {row.published_at ? (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => void resultsApi.withdraw(slug, row.discipline_id).then(load)}
                  >
                    {t("floor.results.withdraw")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void resultsApi.publish(slug, row.discipline_id).then(load)}
                  >
                    {t("floor.results.publish")}
                  </button>
                )}
              </div>
              {row.published_at && <p className="muted">{t("floor.results.withdrawHint")}</p>}
            </>
          )}
        </section>
      ))}
    </div>
  );
}
