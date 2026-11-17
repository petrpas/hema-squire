import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { getToken } from "../../api";
import { DisciplineStrip } from "../DisciplineStrip";
import { FloorLayout } from "../FloorLayout";
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

/** Výsledky: the current discipline's final standing once its bracket
 *  closes, in the work; its export, print and publish gate in the operations
 *  panel (spec floor-results, spec floor-console). */
export default function ResultsTab({
  slug,
  discipline,
  fallback,
}: {
  slug: string;
  discipline?: string;
  /** The discipline kept across the console, for an address naming none. */
  fallback?: string;
}) {
  const { t } = useTranslation();
  const [data, setData] = useState<DisciplineResults[] | null>(null);

  const load = useCallback(() => {
    resultsApi.list(slug).then(setData, () => setData([]));
  }, [slug]);
  useEffect(load, [load]);

  const row =
    data?.find((r) => r.slug === discipline) ??
    data?.find((r) => r.slug === fallback) ??
    data?.[0] ??
    null;

  if (data === null || row === null) {
    // a failed read is stated as nothing to show, as before
    return <FloorLayout tab="results">{data === null && <p>{t("common.loading")}</p>}</FloorLayout>;
  }

  const rail =
    row.standing === null ? (
      <p className="rail-hint">{t("floor.ops.idle.bracketOpen")}</p>
    ) : (
      <section className="rail-card">
        <h2>{row.name}</h2>
        <div className="floor-row-actions">
          <button
            type="button"
            className="secondary"
            onClick={() =>
              void download(resultsApi.exportUrl(slug, row.discipline_id, "csv"), `${row.slug}.csv`)
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
        {row.published_at && <p className="rail-hint">{t("floor.results.withdrawHint")}</p>}
      </section>
    );

  return (
    <FloorLayout
      tab="results"
      className="floor-data"
      head={<DisciplineStrip slug={slug} tab="results" disciplines={data} current={row.slug} />}
      rail={rail}
    >
      <section className="rail-card">
        <h2>
          {row.name}{" "}
          <span className="muted">
            {row.published_at ? t("floor.results.published") : t("floor.results.waiting")}
          </span>
        </h2>
        {row.standing === null ? (
          <p className="muted">{t("floor.results.bracketOpen")}</p>
        ) : (
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
        )}
      </section>
    </FloorLayout>
  );
}
