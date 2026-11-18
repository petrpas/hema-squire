import { IconArrowUp, IconSearch, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { RosterMemberFields } from "./api";
import RosterMemberDialog from "./RosterMemberDialog";
import { type DraftRow, draftRow } from "./roster";

/** A team's members as a draft: one line each — name, HRID, club and the row
 *  actions — and "add a member" while the roster has room. Every member is
 *  named through `RosterMemberDialog`, added or rebound alike (spec: "Member
 *  added through the dialog"). The draft is the caller's, and so is saving it:
 *  the registrant's Teams tab saves every roster at once, the floor's Data
 *  sheet sends a whole team it forms on the day. */
export default function RosterMembers({
  members,
  max,
  onChange,
}: {
  members: DraftRow[];
  /** The discipline's team maximum; null where it states none. */
  max: number | null;
  onChange: (members: DraftRow[]) => void;
}) {
  const { t } = useTranslation();
  // one slot: naming a member happens in the dialog, whether the member is
  // being added or rebound, so the roster itself carries no search block
  const [dialog, setDialog] = useState<{ index: number | null } | null>(null);

  function moveUp(index: number) {
    if (index <= 0) return;
    const next = [...members];
    const above = next[index - 1];
    const member = next[index];
    if (above === undefined || member === undefined) return;
    next[index - 1] = member;
    next[index] = above;
    onChange(next);
  }

  function confirmDialog(member: RosterMemberFields) {
    const index = dialog?.index ?? null;
    onChange(
      index === null
        ? [...members, draftRow(member)]
        : // rebinding is a correction to the member in that row, not a
          // different person: its identity and its React key both stay
          members.map((m, i) => (i === index ? { ...member, id: m.id, rowId: m.rowId } : m)),
    );
    setDialog(null);
  }

  return (
    <>
      <ul className="detail-list">
        {members.map((member, index) => (
          <li key={member.rowId}>
            <div className="checklist-row team-row">
              <input
                className="cell-input"
                value={member.name}
                onChange={(event) =>
                  onChange(
                    members.map((m, i) => (i === index ? { ...m, name: event.target.value } : m)),
                  )
                }
              />
              <span className="muted roster-hrid">
                {member.hr_id !== null ? `HR ${member.hr_id}` : ""}
              </span>
              <span className="muted roster-club">{member.club ?? ""}</span>
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
                onClick={() => onChange(members.filter((_, i) => i !== index))}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </div>
          </li>
        ))}
      </ul>

      {(max === null || members.length < max) && (
        <button type="button" className="link-button" onClick={() => setDialog({ index: null })}>
          {t("roster.add")}
        </button>
      )}

      {dialog && (
        <RosterMemberDialog
          initial={dialog.index === null ? null : (members[dialog.index] ?? null)}
          onConfirm={confirmDialog}
          onClose={() => setDialog(null)}
        />
      )}
    </>
  );
}
