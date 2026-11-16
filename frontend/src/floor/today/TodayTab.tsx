import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import * as routes from "../../routes";
import { checkinApi } from "../floorApi";
import { type FloorTab, isFloorTab } from "../tabs";
import { usePolled } from "../usePolled";

const COLUMNS: FloorTab[] = ["checkin", "pools", "bracket", "results"];

/** Přehled: discipline × step, each cell a link to its step at its
 *  discipline, the slip, and what waits (spec floor-today). Refreshed every
 *  fifteen seconds without a sign of it but the time it last succeeded. */
export default function TodayTab({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation();
  const { data, failed, freshAt } = usePolled(() => checkinApi.today(slug));

  if (data === null) {
    return (
      <p className="floor-not-yet muted">
        {failed ? t("floor.today.failed") : t("common.loading")}
      </p>
    );
  }

  return (
    <div className="floor-data">
      <table className="sheet-table floor-matrix">
        <thead>
          <tr>
            <th scope="col">{t("floor.today.discipline")}</th>
            {COLUMNS.map((step) => (
              <th key={step} scope="col">
                {t(`floor.tabs.${step}`)}
              </th>
            ))}
            <th scope="col">{t("floor.today.slip")}</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.discipline_id}>
              <th scope="row">{row.name}</th>
              {COLUMNS.map((step) => (
                <td key={step}>
                  <Link to={routes.floorPath(slug, step, row.slug)}>
                    {t(`floor.today.state.${row.steps[step] ?? "waiting"}`)}
                  </Link>
                </td>
              ))}
              <td>
                {row.slip === null
                  ? ""
                  : t(row.slip > 0 ? "floor.today.behind" : "floor.today.ahead", {
                      count: Math.abs(row.slip),
                    })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className="rail-card">
        <h2>{t("floor.today.waiting")}</h2>
        {data.waiting.length === 0 ? (
          <p className="muted">{t("floor.today.nothing")}</p>
        ) : (
          <ul>
            {data.waiting.map((item) => (
              <li key={`${item.tab}-${item.discipline ?? ""}-${item.code}`}>
                <Link
                  to={routes.floorPath(
                    slug,
                    isFloorTab(item.tab) ? item.tab : "today",
                    item.discipline ?? undefined,
                  )}
                >
                  {t(`floor.today.codes.${item.code}`, {
                    discipline:
                      data.rows.find((r) => r.slug === item.discipline)?.name ??
                      item.discipline ??
                      "",
                  })}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {freshAt !== null && (
        <p className="muted">
          {failed
            ? t("floor.today.stale", {
                time: freshAt.toLocaleTimeString(i18n.language, {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
              })
            : t("floor.today.fresh", {
                time: freshAt.toLocaleTimeString(i18n.language, {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
              })}
        </p>
      )}
    </div>
  );
}
