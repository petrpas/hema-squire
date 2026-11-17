import { useTranslation } from "react-i18next";

import type { StatsRow } from "../floorApi";

/** Standings by the adopted calculation: V, M, V/M, TS, TR, index. Where a
 *  cut is given, the rows below it are stated as not advancing. */
export function StatsTable({
  rows,
  name,
  cut,
}: {
  rows: StatsRow[];
  name: (key: string) => string;
  cut?: number;
}) {
  const { t } = useTranslation();
  return (
    <table className="sheet-table floor-stats">
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">{t("floor.data.name")}</th>
          <th scope="col">V</th>
          <th scope="col">M</th>
          <th scope="col">V/M</th>
          <th scope="col">TS</th>
          <th scope="col">TR</th>
          <th scope="col">{t("floor.pools.index")}</th>
          {cut !== undefined && <th scope="col">{t("floor.pools.advances")}</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={row.key}>
            <td>{index + 1}</td>
            <th scope="row">{name(row.key)}</th>
            <td>{row.v}</td>
            <td>{row.m}</td>
            <td>{row.vm.toFixed(2)}</td>
            <td>{row.ts}</td>
            <td>{row.tr}</td>
            <td>{row.ind}</td>
            {cut !== undefined && (
              <td>{index < cut ? t("floor.pools.yes") : t("floor.pools.no")}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
