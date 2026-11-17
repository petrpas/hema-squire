import { useState } from "react";
import { useTranslation } from "react-i18next";

import { DisciplineStrip } from "../DisciplineStrip";
import { FloorLayout } from "../FloorLayout";
import { checkinApi } from "../floorApi";
import { usePolled } from "../usePolled";
import { DisciplineGate } from "./DisciplineGate";
import { LineupEditor } from "./LineupEditor";
import { PersonRow } from "./PersonRow";

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/** The desk (spec floor-checkin): every person once, searchable by name and
 *  club, a tick for arrival, withdrawals per entry, team lineups. The strip
 *  chooses a discipline, "Všichni" first; at a discipline only its entrants
 *  are listed. The close gate of the discipline, or of each under "Všichni",
 *  is the tab's operation, in its panel (spec floor-console). */
export default function CheckinTab({ slug, discipline }: { slug: string; discipline?: string }) {
  const { t, i18n } = useTranslation();
  const { data, failed, freshAt, reload } = usePolled(() => checkinApi.desk(slug));
  const [search, setSearch] = useState("");
  const [error, setError] = useState(false);

  if (data === null) {
    return (
      <FloorLayout tab="checkin">
        <p className="floor-not-yet muted">
          {failed ? t("floor.checkin.failed") : t("common.loading")}
        </p>
      </FloorLayout>
    );
  }

  const selected = data.disciplines.find((d) => d.slug === discipline);
  const names = new Map(data.disciplines.map((d) => [d.id, d.name]));
  const closed = new Set(data.disciplines.filter((d) => d.closed).map((d) => d.id));
  const needle = fold(search.trim());
  const persons = data.persons.filter(
    (p) =>
      (selected === undefined || p.entries.some((e) => e.discipline_id === selected.id)) &&
      (needle === "" || fold(`${p.name} ${p.club ?? ""}`).includes(needle)),
  );

  async function act(action: () => Promise<unknown>) {
    setError(false);
    try {
      await action();
    } catch {
      setError(true);
    }
    reload();
  }

  const head = (
    <>
      <DisciplineStrip
        slug={slug}
        tab="checkin"
        disciplines={data.disciplines}
        current={selected?.slug ?? null}
        all
      />
      <label className="floor-search">
        {t("floor.checkin.search")}
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} />
      </label>
    </>
  );
  const rail = data.disciplines
    .filter((d) => selected === undefined || d.id === selected.id)
    .map((d) => <DisciplineGate key={d.id} slug={slug} discipline={d} onChanged={reload} />);

  return (
    <FloorLayout tab="checkin" className="floor-data floor-checkin" head={head} rail={rail}>
      {error && (
        <p className="save-bar-error" role="alert">
          {t("floor.plan.failed")}
        </p>
      )}

      <table className="sheet-table floor-desk">
        <thead>
          <tr>
            <th scope="col">{t("floor.checkin.arrived")}</th>
            <th scope="col">{t("floor.data.name")}</th>
            <th scope="col">{t("floor.data.club")}</th>
            <th scope="col">{t("floor.checkin.entries")}</th>
          </tr>
        </thead>
        <tbody>
          {persons.map((person) => (
            <PersonRow
              key={person.key}
              person={person}
              names={names}
              closed={closed}
              onArrive={(here) =>
                void act(() =>
                  here ? checkinApi.arrive(slug, person.key) : checkinApi.leave(slug, person.key),
                )
              }
              onWithdraw={(entry, out) =>
                void act(() =>
                  out ? checkinApi.withdraw(slug, entry) : checkinApi.undoWithdrawal(slug, entry),
                )
              }
            />
          ))}
        </tbody>
      </table>

      {data.teams
        .filter((team) => selected === undefined || team.discipline_id === selected.id)
        .map((team) => (
          <LineupEditor
            key={team.key}
            slug={slug}
            team={team}
            persons={data.persons}
            discipline={data.disciplines.find((d) => d.id === team.discipline_id)}
            onChanged={reload}
          />
        ))}

      {freshAt !== null && (
        <p className="muted">
          {t(failed ? "floor.today.stale" : "floor.today.fresh", {
            time: freshAt.toLocaleTimeString(i18n.language, { hour: "2-digit", minute: "2-digit" }),
          })}
        </p>
      )}
    </FloorLayout>
  );
}
