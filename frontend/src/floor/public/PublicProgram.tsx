import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type ProgramItem, publicFloorApi } from "../floorApi";

/** An item's label as a translation key and its values. */
function itemLabel(item: ProgramItem): [string, Record<string, number>] {
  if (item.kind === "pool") return ["floor.public.pool", { number: item.ordinal }];
  if (item.final) return ["floor.public.final", {}];
  return ["floor.public.round", { round: item.round }];
}

/** Program: the published plan by discipline, its times in the tournament's
 *  zone and its slip once the day runs (spec floor-public). */
export function PublicProgram({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [data, setData] = useState<Awaited<ReturnType<typeof publicFloorApi.program>> | null>(null);
  useEffect(() => {
    publicFloorApi.program(slug).then(setData, () => setData([]));
  }, [slug]);
  if (data === null) return <p>{t("common.loading")}</p>;
  return (
    <div className="floor-public">
      {data.map((discipline) => (
        <section key={discipline.slug}>
          <h2>
            {discipline.discipline}
            {discipline.slip !== null && discipline.slip > 0 && (
              <span className="muted"> {t("floor.public.slip", { count: discipline.slip })}</span>
            )}
          </h2>
          <table className="sheet-table">
            <tbody>
              {discipline.items.map((item) => (
                <tr key={`${item.kind}-${item.round}-${item.ordinal}-${item.start}`}>
                  <td>{item.day}</td>
                  <td>
                    {item.start}–{item.end}
                  </td>
                  <th scope="row">{t(...itemLabel(item))}</th>
                  <td>{item.piste}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
