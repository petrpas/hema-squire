import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type RosterMemberFields, type TeamEntry } from "./api";
import { useManageKey } from "./manageKey";
import RosterMembers from "./RosterMembers";
import { type DraftRow, draftRow, rosterChanged, summarizeSaves, toRosterInput } from "./roster";

function initialRoster(team: TeamEntry): DraftRow[] {
  const members: (RosterMemberFields & { id?: number })[] =
    team.members.length > 0 ? team.members : team.prefill ? [team.prefill] : [];
  return members.map(draftRow);
}

/** One team's roster in the draft `TeamsTab` holds for it — the save lives on
 *  the tab, not here (design D2). */
function RosterEditor({
  team,
  members,
  onChange,
}: {
  team: TeamEntry;
  members: DraftRow[];
  onChange: (members: DraftRow[]) => void;
}) {
  const { t } = useTranslation();
  const shortfall = Math.max(team.team_min - members.length, 0);

  return (
    <div className="rail-card">
      <h3 className="register-section">{t("roster.title", { team: team.name })}</h3>
      <p className="rail-hint">{t("roster.bounds", { min: team.team_min, max: team.team_max })}</p>
      {shortfall > 0 && <p className="rail-hint">{t("roster.shortfall", { count: shortfall })}</p>}
      <RosterMembers members={members} max={team.team_max} onChange={onChange} />
    </div>
  );
}

/** The tab holding every roster editor for the fencer's active registration,
 *  one per team in registration order, saved together (spec: "Rosters are
 *  edited on the detail page's Teams tab", "One save commits every roster on
 *  the tab"). Draft state is lifted here, keyed by team id, so one save can
 *  fan out over whichever teams changed (design D2, D3, D4). */
export default function TeamsTab({
  slug,
  teams,
  onTeamUpdated,
}: {
  slug: string;
  teams: TeamEntry[];
  onTeamUpdated: (team: TeamEntry) => void;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Map<number, DraftRow[]>>(
    () => new Map(teams.map((team) => [team.id, initialRoster(team)])),
  );
  const [busy, setBusy] = useState(false);
  const [failedTeams, setFailedTeams] = useState<string[] | null>(null);
  const manageKey = useManageKey();

  // a team can appear or disappear from under the tab through an amendment;
  // seed a draft for any newcomer and drop drafts for teams no longer held
  useEffect(() => {
    setDrafts((prev) => {
      let changed = false;
      const next = new Map(prev);
      for (const team of teams) {
        if (!next.has(team.id)) {
          next.set(team.id, initialRoster(team));
          changed = true;
        }
      }
      for (const id of next.keys()) {
        if (!teams.some((team) => team.id === id)) {
          next.delete(id);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [teams]);

  const dirtyTeams = teams.filter((team) => rosterChanged(team.members, drafts.get(team.id) ?? []));

  async function saveAll() {
    setBusy(true);
    setFailedTeams(null);
    const results = await Promise.allSettled(
      dirtyTeams.map((team) =>
        api.updateRoster(slug, team.id, (drafts.get(team.id) ?? []).map(toRosterInput), manageKey),
      ),
    );
    const { saved, failed } = summarizeSaves(
      dirtyTeams.flatMap((team, index) => {
        const result = results[index];
        return result === undefined ? [] : [{ team, result }];
      }),
    );
    // reseed each saved draft from the server's answer: the stored roster may
    // differ from what was sent (normalized fields, a prefill now stored), and
    // a member saved just now gets its id here — so the tab reads clean and
    // the save greys out until the next edit
    if (saved.length > 0) {
      setDrafts((prev) => {
        const next = new Map(prev);
        for (const team of saved) next.set(team.id, initialRoster(team));
        return next;
      });
    }
    for (const team of saved) onTeamUpdated(team);
    setFailedTeams(failed.length > 0 ? failed : null);
    setBusy(false);
  }

  return (
    <div className="teams-tab">
      {teams.map((team) => (
        <RosterEditor
          key={team.id}
          team={team}
          members={drafts.get(team.id) ?? []}
          onChange={(members) => setDrafts((prev) => new Map(prev).set(team.id, members))}
        />
      ))}

      {failedTeams && (
        <p className="login-error">
          {t("roster.saveFailedTeams", { teams: failedTeams.join(", ") })}
        </p>
      )}
      <button
        type="button"
        className="btn-primary param-save param-save-inline"
        disabled={busy || dirtyTeams.length === 0}
        onClick={() => void saveAll()}
      >
        {t("roster.saveAll")}
      </button>
    </div>
  );
}
