import { useState } from "react";
import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import RosterMembers from "../../RosterMembers";
import type { DraftRow } from "../../roster";
import type { DataSheet, SheetMember } from "../floorApi";

/** "Přidat tým": a team formed on the day, its name and its members, named
 *  through the registrant's own roster editor (`RosterMembers`). A member
 *  found in HEMA Ratings who already stands on the floor is that person — the
 *  server binds by HR ID — anyone else is a floor-only newcomer. Nothing
 *  added here reaches the office (spec floor-data, The sheet is the floor's
 *  to correct). */
export default function AddTeam({
  sheet,
  onAdd,
}: {
  sheet: DataSheet;
  /** Resolves false where the server refused, so the dialog stays open. */
  onAdd: (name: string, members: SheetMember[]) => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [members, setMembers] = useState<DraftRow[]>([]);
  const [failed, setFailed] = useState(false);
  const min = sheet.discipline.team_min ?? 1;
  const max = sheet.discipline.team_max ?? null;
  const named = members.filter((member) => member.name.trim() !== "");
  const label = t("floor.data.addTeam");

  function close() {
    setOpen(false);
    setName("");
    setMembers([]);
    setFailed(false);
  }

  async function submit() {
    const sent = named.map(({ name: memberName, hr_id, club, nationality }) => ({
      person: { name: memberName.trim(), hr_id, club, nationality },
    }));
    if (await onAdd(name.trim(), sent)) close();
    else setFailed(true);
  }

  return (
    <>
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        {label}
      </button>
      {open && (
        <Modal onClose={close}>
          <div className="modal floor-add">
            <h2>{label}</h2>
            <label>
              {t("floor.data.teamName")}
              <input
                value={name}
                maxLength={200}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            {max !== null && <p className="rail-hint">{t("roster.bounds", { min, max })}</p>}
            <RosterMembers members={members} max={max} onChange={setMembers} />
            {failed && (
              <p className="save-bar-error" role="alert">
                {t("floor.data.teamRefused")}
              </p>
            )}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={close}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={name.trim() === "" || named.length < min}
                onClick={() => void submit()}
              >
                {label}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
