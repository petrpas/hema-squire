import { useState } from "react";
import { useTranslation } from "react-i18next";

import { checkinApi, type DeskDiscipline, type DeskPerson, type DeskTeam } from "../floorApi";

/** A team's lineup for the day: chosen from its members, with a substitute
 *  named at the desk as a floor-only person (spec floor-checkin, A team
 *  fields a lineup for the day). The office's roster is never changed. */
export function LineupEditor({
  slug,
  team,
  persons,
  discipline,
  onChanged,
}: {
  slug: string;
  team: DeskTeam;
  persons: DeskPerson[];
  discipline: DeskDiscipline | undefined;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [substitute, setSubstitute] = useState("");
  const [failed, setFailed] = useState(false);
  const name = new Map(persons.map((p) => [p.key, p.name]));
  const arrived = new Set(persons.filter((p) => p.arrived).map((p) => p.key));
  const candidates = [...new Set([...team.members, ...team.lineup])];
  const locked = discipline?.closed ?? false;

  async function save(keys: string[]) {
    setFailed(false);
    try {
      await checkinApi.lineup(slug, team.key, keys);
    } catch {
      setFailed(true);
    }
    onChanged();
  }

  async function addSubstitute() {
    const trimmed = substitute.trim();
    if (trimmed === "") return;
    try {
      const { key } = await checkinApi.local(slug, trimmed);
      setSubstitute("");
      await save([...team.lineup, key]);
    } catch {
      setFailed(true);
    }
  }

  return (
    <section className="rail-card floor-lineup">
      <h2>
        {team.name}{" "}
        <span className="muted">
          {team.present
            ? t("floor.checkin.teamPresent")
            : t("floor.checkin.teamShort", { count: team.short_by })}
        </span>
      </h2>
      <fieldset className="floor-ticks" disabled={locked}>
        <legend>
          {t("floor.checkin.lineup", {
            min: discipline?.team_min ?? 1,
            max: discipline?.team_max ?? "",
          })}
        </legend>
        {candidates.map((key) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={team.lineup.includes(key)}
              onChange={(event) =>
                void save(
                  event.target.checked
                    ? [...team.lineup, key]
                    : team.lineup.filter((other) => other !== key),
                )
              }
            />
            {name.get(key) ?? key}
            {arrived.has(key) && <span className="muted"> {t("floor.checkin.here")}</span>}
          </label>
        ))}
      </fieldset>
      {!locked && (
        <div className="floor-row">
          <label>
            {t("floor.checkin.substitute")}
            <input
              value={substitute}
              maxLength={200}
              onChange={(event) => setSubstitute(event.target.value)}
            />
          </label>
          <button type="button" className="secondary" onClick={() => void addSubstitute()}>
            {t("floor.checkin.addSubstitute")}
          </button>
        </div>
      )}
      {failed && (
        <p className="save-bar-error" role="alert">
          {t("floor.checkin.lineupRefused")}
        </p>
      )}
    </section>
  );
}
