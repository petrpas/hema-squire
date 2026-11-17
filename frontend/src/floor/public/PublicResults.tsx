import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { publicFloorApi } from "../floorApi";

/** Výsledky: the published standings with name, club and nationality (spec
 *  floor-public). */
export function PublicResults({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [data, setData] = useState<Awaited<ReturnType<typeof publicFloorApi.results>> | null>(null);
  useEffect(() => {
    publicFloorApi.results(slug).then(setData, () => setData([]));
  }, [slug]);
  if (data === null) return <p>{t("common.loading")}</p>;
  return (
    <div className="floor-public">
      {data.map((discipline) => (
        <section key={discipline.slug}>
          <h2>{discipline.discipline}</h2>
          <table className="sheet-table">
            <tbody>
              {discipline.standing.map((row) => (
                <tr key={`${row.place}-${row.name}`}>
                  <td>{row.place}.</td>
                  <th scope="row">{row.name}</th>
                  <td>{row.club}</td>
                  <td>{row.nationality}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
