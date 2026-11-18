import { useState } from "react";
import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import RosterMemberDialog from "../../RosterMemberDialog";
import type { DataSheet, NewSheetPerson, SheetMember } from "../floorApi";

/** "Přidat účastníka" on an individual discipline: someone already on the
 *  floor, or a new floor-only person (spec floor-data, The sheet is the
 *  floor's to correct). A new person is named as a registrant names a team
 *  member: the name typed once, looked up in HEMA Ratings or taken as typed
 *  (`RosterMemberDialog`). A team discipline adds a whole team (`AddTeam`).
 *  Nothing added here reaches the office. */
export default function AddEntrant({
  sheet,
  onAdd,
}: {
  sheet: DataSheet;
  /** Resolves false where the server refused, so the dialog stays open. */
  onAdd: (name: string, members: SheetMember[]) => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [naming, setNaming] = useState(false);
  const [picked, setPicked] = useState<string | null>(null);
  const [fresh, setFresh] = useState<NewSheetPerson | null>(null);
  const [failed, setFailed] = useState(false);
  // whoever already stands in the discipline is not offered again
  const entered = new Set(sheet.rows.map((row) => row.person));
  const candidates = sheet.persons.filter((p) => !entered.has(p.key));
  const member: SheetMember | null =
    picked !== null ? { person_key: picked } : fresh !== null ? { person: fresh } : null;
  const label = t("floor.data.add");

  function close() {
    setOpen(false);
    setNaming(false);
    setPicked(null);
    setFresh(null);
    setFailed(false);
  }

  async function submit() {
    if (member === null) return;
    if (await onAdd("", [member])) close();
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
            {candidates.length > 0 && (
              <fieldset className="floor-add-people">
                <legend>{t("floor.data.onTheFloor")}</legend>
                {candidates.map((person) => (
                  <label key={person.key}>
                    <input
                      type="radio"
                      name="floor-add-person"
                      checked={picked === person.key}
                      onChange={() => {
                        // picking someone on the floor replaces a named newcomer
                        setFresh(null);
                        setPicked(person.key);
                      }}
                    />
                    {person.name}
                    {person.club && <span className="muted"> {person.club}</span>}
                  </label>
                ))}
              </fieldset>
            )}
            <fieldset>
              <legend>{t("floor.data.newPerson")}</legend>
              {fresh !== null ? (
                <p className="floor-add-new">
                  <span>
                    {fresh.name}
                    {fresh.club && <span className="muted"> {fresh.club}</span>}
                    {fresh.hr_id != null && <span className="muted"> HR {fresh.hr_id}</span>}
                  </span>
                  <button type="button" className="link-button" onClick={() => setFresh(null)}>
                    {t("floor.data.remove")}
                  </button>
                </p>
              ) : (
                <button type="button" className="secondary" onClick={() => setNaming(true)}>
                  {t("roster.addTitle")}
                </button>
              )}
            </fieldset>
            {failed && (
              <p className="save-bar-error" role="alert">
                {t("floor.data.addRefused")}
              </p>
            )}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={close}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={member === null}
                onClick={() => void submit()}
              >
                {label}
              </button>
            </div>
          </div>
        </Modal>
      )}
      {naming && (
        <RosterMemberDialog
          initial={null}
          onConfirm={(person) => {
            setNaming(false);
            setPicked(null);
            setFresh(person);
          }}
          onClose={() => setNaming(false)}
        />
      )}
    </>
  );
}
