import { IconArrowUp, IconSearch, IconX } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import RosterMemberDialog from "./RosterMemberDialog";
import { type RosterMember, type TeamEntry, api } from "./api";
import { rosterChanged, summarizeSaves } from "./roster";

function initialRoster(team: TeamEntry): RosterMember[] {
  return team.members.length > 0 ? team.members : team.prefill ? [team.prefill] : [];
}

/** Adds, removes, renames, rebinds, and reorders a team's roster in the
 *  draft `TeamsTab` holds for it — the save lives on the tab, not here
 *  (design D2). */
function RosterEditor({
  team,
  members,
  onChange,
}: {
  team: TeamEntry;
  members: RosterMember[];
  onChange: (members: RosterMember[]) => void;
}) {
  const { t } = useTranslation();
  // one slot: naming a member happens in the dialog, whether the member is
  // being added or rebound, so the roster itself carries no name field and no
  // search block (spec: "Member added through the dialog")
  const [dialog, setDialog] = useState<{ index: number | null } | null>(null);

  function renameMember(index: number, name: string) {
    onChange(members.map((m, i) => (i === index ? { ...m, name } : m)));
  }

  function removeMember(index: number) {
    onChange(members.filter((_, i) => i !== index));
  }

  function moveMemberUp(index: number) {
    if (index <= 0) return;
    const next = [...members];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    onChange(next);
  }

  function confirmDialog(member: RosterMember) {
    const index = dialog?.index ?? null;
    onChange(index === null ? [...members, member] : members.map((m, i) => (i === index ? member : m)));
    setDialog(null);
  }

  const shortfall = Math.max(team.team_min - members.length, 0);

  return (
    <div className="rail-card">
      <h3 className="register-section">{t("roster.title", { team: team.name })}</h3>
      <p className="rail-hint">{t("roster.bounds", { min: team.team_min, max: team.team_max })}</p>
      {shortfall > 0 && <p className="rail-hint">{t("roster.shortfall", { count: shortfall })}</p>}

      {/* one line per member: their name, their HRID, their club, their row actions */}
      <ul className="detail-list">
        {members.map((member, index) => (
          <li key={index}>
            <div className="checklist-row team-row">
              <input
                className="cell-input"
                value={member.name}
                onChange={(event) => renameMember(index, event.target.value)}
              />
              <span className="muted roster-hrid">{member.hr_id !== null ? `#${member.hr_id}` : ""}</span>
              <span className="muted roster-club">{member.club ?? ""}</span>
              <button
                type="button"
                className="row-action"
                title={t("actions.moveUp")}
                disabled={index === 0}
                onClick={() => moveMemberUp(index)}
              >
                <IconArrowUp size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("roster.rebind")}
                onClick={() => setDialog({ index })}
              >
                <IconSearch size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("actions.delete")}
                onClick={() => removeMember(index)}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </div>
          </li>
        ))}
      </ul>

      {members.length < team.team_max && (
        <button type="button" className="link-button" onClick={() => setDialog({ index: null })}>
          {t("roster.add")}
        </button>
      )}

      {dialog && (
        <RosterMemberDialog
          initial={dialog.index === null ? null : members[dialog.index]}
          onConfirm={confirmDialog}
          onClose={() => setDialog(null)}
        />
      )}
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
  const [drafts, setDrafts] = useState<Map<number, RosterMember[]>>(
    () => new Map(teams.map((team) => [team.id, initialRoster(team)])),
  );
  const [busy, setBusy] = useState(false);
  const [failedTeams, setFailedTeams] = useState<string[] | null>(null);

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
        api.updateRoster(
          slug,
          team.id,
          (drafts.get(team.id) ?? []).map((member) => ({
            name: member.name,
            hr_id: member.hr_id,
            club: member.club,
            nationality: member.nationality,
          })),
        ),
      ),
    );
    const { saved, failed } = summarizeSaves(
      dirtyTeams.map((team, index) => ({ team, result: results[index] })),
    );
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
        <p className="login-error">{t("roster.saveFailedTeams", { teams: failedTeams.join(", ") })}</p>
      )}
      <button
        className="btn-primary param-save param-save-inline"
        disabled={busy || dirtyTeams.length === 0}
        onClick={() => void saveAll()}
      >
        {t("roster.saveAll")}
      </button>
    </div>
  );
}
