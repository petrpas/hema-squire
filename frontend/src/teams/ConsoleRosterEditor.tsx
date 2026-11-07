import { IconArrowUp, IconSearch, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ConsoleTeam, type ConsoleTeamDiscipline, type RosterMemberFields } from "../api";
import RosterMemberDialog from "../RosterMemberDialog";
import { type DraftRow, draftRow, rosterChanged, toRosterInput } from "../roster";

/** The organizer's roster editor: the same four fields and the same draft the
 *  entering fencer edits, with the members off the roster beside it so one
 *  removed by mistake can be restored rather than re-typed.
 *
 *  A team arrives at the venue and the fencer who entered it cannot reach
 *  their own editor; the organizer acting for them is the remedy, and a safe
 *  one — a roster edit moves no money and sends no mail (spec
 *  team-disciplines, Roster editing changes no money). */
export default function ConsoleRosterEditor({
  slug,
  team,
  discipline,
  onSaved,
  onClose,
}: {
  slug: string;
  team: ConsoleTeam;
  discipline: ConsoleTeamDiscipline;
  onSaved: (team: ConsoleTeam) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [members, setMembers] = useState<DraftRow[]>(() => team.members.map(draftRow));
  const [dialog, setDialog] = useState<{ index: number | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  // a restored member is a member of the roster the save states, so the
  // maximum refuses a restore into a full roster the way it refuses any
  // roster too large
  const restorable = team.removed_members.filter(
    (gone) => !members.some((member) => member.id === gone.id),
  );
  const room = members.length < discipline.team_max;
  const changed = rosterChanged(team.members, members);

  function moveUp(index: number) {
    if (index <= 0) return;
    const next = [...members];
    const above = next[index - 1];
    const member = next[index];
    if (above === undefined || member === undefined) return;
    next[index - 1] = member;
    next[index] = above;
    setMembers(next);
  }

  function confirmDialog(member: RosterMemberFields) {
    const index = dialog?.index ?? null;
    setMembers(
      index === null
        ? [...members, draftRow(member)]
        : // rebinding corrects the member in that row; it is not a different
          // person, so its identity stays
          members.map((m, i) => (i === index ? { ...member, id: m.id, rowId: m.rowId } : m)),
    );
    setDialog(null);
  }

  async function save() {
    setBusy(true);
    setFailed(null);
    try {
      onSaved(await api.consoleUpdateRoster(slug, team.id, members.map(toRosterInput)));
    } catch {
      setFailed(t("teams.editor.saveFailed"));
    }
    setBusy(false);
  }

  return (
    <div className="roster-editor">
      <p className="rail-hint">{t("teams.editor.movesNoMoney")}</p>
      <ul className="detail-list">
        {members.map((member, index) => (
          <li key={member.rowId}>
            <div className="checklist-row team-row">
              <input
                className="cell-input"
                value={member.name}
                onChange={(event) =>
                  setMembers(
                    members.map((m, i) => (i === index ? { ...m, name: event.target.value } : m)),
                  )
                }
              />
              <span className="muted roster-hrid">
                {member.hr_id !== null ? `#${member.hr_id}` : ""}
              </span>
              <span className="muted roster-club">{member.club ?? ""}</span>
              <span className="muted roster-nationality">{member.nationality ?? ""}</span>
              <button
                type="button"
                className="row-action"
                title={t("actions.moveUp")}
                disabled={index === 0}
                onClick={() => moveUp(index)}
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
                onClick={() => setMembers(members.filter((_, i) => i !== index))}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </div>
          </li>
        ))}
      </ul>

      {room && (
        <button type="button" className="link-button" onClick={() => setDialog({ index: null })}>
          {t("roster.add")}
        </button>
      )}

      {restorable.length > 0 && (
        <>
          <p className="rail-hint">{t("teams.editor.removedTitle")}</p>
          <ul className="detail-list">
            {restorable.map((gone) => (
              <li key={gone.id} className="muted">
                <div className="checklist-row team-row">
                  <span>
                    {gone.name}
                    {gone.hr_id !== null && ` · #${gone.hr_id}`}
                    {gone.club && ` · ${gone.club}`}
                  </span>
                  <span className="muted">
                    {gone.removed_by
                      ? t("teams.editor.removedBy", {
                          name: gone.removed_by,
                          at: new Date(gone.removed_at).toLocaleString(),
                        })
                      : new Date(gone.removed_at).toLocaleString()}
                  </span>
                  <button
                    type="button"
                    className="link-button"
                    disabled={!room}
                    onClick={() => setMembers([...members, draftRow(gone)])}
                  >
                    {t("teams.editor.restore")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {failed && <p className="login-error">{failed}</p>}
      <div className="detail-row">
        <button
          type="button"
          className="btn-primary param-save param-save-inline"
          disabled={busy || !changed}
          onClick={() => void save()}
        >
          {t("teams.editor.save")}
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          {t("common.cancel")}
        </button>
      </div>

      {dialog && (
        <RosterMemberDialog
          initial={dialog.index === null ? null : (members[dialog.index] ?? null)}
          onConfirm={confirmDialog}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  );
}
