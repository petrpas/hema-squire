import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ApiError } from "../../api";
import * as routes from "../../routes";
import { FloorLayout } from "../FloorLayout";
import { type FloorPerson, type FloorRoster, floorApi } from "../floorApi";

/** Who the floor will work with: the floor roster, read live on every open,
 *  per discipline (spec floor-data). Entrants come from the office only; an
 *  organizer-kept tournament is pointed to its Import phase. */
export default function DataTab({
  slug,
  keptByOrganizer,
}: {
  slug: string;
  keptByOrganizer: boolean;
}) {
  const { t } = useTranslation();
  const [roster, setRoster] = useState<FloorRoster | null | "draft" | "error">(null);

  useEffect(() => {
    floorApi
      .roster(slug)
      .then(setRoster, (error) =>
        setRoster(error instanceof ApiError && error.status === 409 ? "draft" : "error"),
      );
  }, [slug]);

  // the entrants of an organizer-kept tournament are changed in the office's
  // Import phase: the tab's one operation, in its panel (spec floor-console)
  const rail = keptByOrganizer ? (
    <section className="rail-card">
      <p>{t("floor.data.fromImport")}</p>
      <Link to={routes.consolePath(slug, "import")}>{t("floor.data.toImport")}</Link>
    </section>
  ) : undefined;
  const source = keptByOrganizer ? null : (
    <p className="muted">{t("floor.data.fromRegistrations")}</p>
  );

  if (roster === null || roster === "draft" || roster === "error") {
    return (
      <FloorLayout tab="data" className="floor-data" rail={rail}>
        {roster === null ? (
          <p>{t("common.loading")}</p>
        ) : (
          <p className="muted">
            {roster === "draft" ? t("floor.data.draft") : t("floor.data.loadFailed")}
          </p>
        )}
      </FloorLayout>
    );
  }

  const persons = new Map(roster.persons.map((person) => [person.key, person]));

  return (
    <FloorLayout tab="data" className="floor-data" rail={rail}>
      {source}
      {roster.disciplines.map((discipline) => {
        const individuals = roster.individuals.filter((e) => e.discipline === discipline.slug);
        const teams = roster.teams.filter((e) => e.discipline === discipline.slug);
        const count = discipline.kind === "team" ? teams.length : individuals.length;
        return (
          <section key={discipline.id} className="rail-card">
            <h2>
              {discipline.name} <span className="muted">{t("floor.data.count", { count })}</span>
            </h2>
            {count === 0 ? (
              <p className="muted">{t("floor.data.empty")}</p>
            ) : (
              <table className="sheet-table">
                <thead>
                  <tr>
                    <th scope="col">{t("floor.data.name")}</th>
                    <th scope="col">{t("floor.data.club")}</th>
                    <th scope="col">{t("floor.data.nationality")}</th>
                    {discipline.kind === "individual" && (
                      <th scope="col">{t("floor.data.rating")}</th>
                    )}
                    <th scope="col">{t("floor.data.paid")}</th>
                  </tr>
                </thead>
                <tbody>
                  {discipline.kind === "individual"
                    ? individuals.map((entry) => (
                        <PersonRow
                          key={entry.person}
                          person={persons.get(entry.person)}
                          rating={entry.rating}
                          paid={entry.paid}
                        />
                      ))
                    : teams.map((team) => (
                        <TeamRows key={team.key} team={team} persons={persons} />
                      ))}
                </tbody>
              </table>
            )}
          </section>
        );
      })}
    </FloorLayout>
  );
}

function PersonRow({
  person,
  rating,
  paid,
}: {
  person: FloorPerson | undefined;
  rating?: number | null;
  paid?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <tr>
      <td>{person?.name}</td>
      <td>{person?.club}</td>
      <td>{person?.nationality}</td>
      {rating !== undefined && <td>{rating === null ? "" : rating.toFixed(1)}</td>}
      <td>{paid === undefined ? "" : paid ? t("floor.data.yes") : ""}</td>
    </tr>
  );
}

function TeamRows({
  team,
  persons,
}: {
  team: FloorRoster["teams"][number];
  persons: Map<string, FloorPerson>;
}) {
  const { t } = useTranslation();
  return (
    <>
      <tr className="floor-team-row">
        <th scope="rowgroup" colSpan={3}>
          {team.name}
        </th>
        <td>{team.paid ? t("floor.data.yes") : ""}</td>
      </tr>
      {team.members.map((key) => (
        <PersonRow key={key} person={persons.get(key)} />
      ))}
    </>
  );
}
