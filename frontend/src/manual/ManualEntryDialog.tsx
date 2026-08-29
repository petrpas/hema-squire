import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type ManualEntryIn, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkNumeric, checkString } from "../validation";
import { parseInteger } from "../numeric";
import { nowInZone } from "./nowInZone";

/** A fencer entered by hand, from the tournament's own structure: its offered
 *  individual disciplines, the items it lends, the afterparty where it holds
 *  one. A choice the tournament does not offer is never presented (spec
 *  etl-console, Manual entry fields follow the tournament's structure).
 *
 *  Acceptance is the server's to decide: the checks here only spare a round
 *  trip for what the client can see, and a refusal the client could not
 *  predict is rendered against the field the server names (design D5).
 */
export default function ManualEntryDialog({
  detail,
  slug,
  onEntered,
  onClose,
}: {
  detail: TournamentDetail;
  slug: string;
  onEntered: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { errors, touch, clearIfValid, validateAll, applyApiErrors } = useFieldValidation();
  const [name, setName] = useState("");
  const [nationality, setNationality] = useState("");
  const [club, setClub] = useState("");
  const [hrId, setHrId] = useState("");
  const [email, setEmail] = useState("");
  const [registeredAt, setRegisteredAt] = useState(() => nowInZone(detail.timezone));
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [rentals, setRentals] = useState<string[]>([]);
  const [afterparty, setAfterparty] = useState(false);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [refusal, setRefusal] = useState<string | null>(null);

  // a team is entered through the tournament's team handling, never by naming
  // a team discipline on a fencer's row
  const offered = detail.disciplines.filter((discipline) => discipline.kind === "individual");
  const lent = detail.extra_items.filter((item) => item.category === "rental");
  const holdsAfterparty = detail.extra_items.some((item) => item.category === "afterparty");

  const checkName = () => checkString("name", "ManualEntryIn.name", name, { required: true });
  const checkClub = () => checkString("club", "ManualEntryIn.club", club);
  const checkNationality = () =>
    checkString("nationality", "ManualEntryIn.nationality", nationality);
  const checkNotes = () =>
    checkString("notes", "ManualEntryIn.notes", notes, { multiline: true });
  const checkHrId = () => checkNumeric("hr_id", "ManualEntryIn.hr_id", hrId);

  function toggle(list: string[], value: string, set: (next: string[]) => void) {
    set(list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);
  }

  async function submit() {
    setRefusal(null);
    const invalid = validateAll([checkName, checkClub, checkNationality, checkNotes, checkHrId]);
    if (invalid > 0) return;
    if (disciplines.length === 0) {
      setRefusal(t("manualEntry.refusal.no_disciplines"));
      return;
    }
    const parsedHrId = hrId.trim() === "" ? null : parseInteger(hrId);
    const entry: ManualEntryIn = {
      name: name.trim(),
      nationality: nationality.trim() || null,
      club: club.trim() || null,
      hr_id: parsedHrId && parsedHrId.ok ? parsedHrId.value : null,
      email: email.trim() || null,
      registered_at: registeredAt || null,
      disciplines,
      weapon_rentals: rentals,
      afterparty,
      notes: notes.trim() || null,
    };
    setBusy(true);
    try {
      await api.createManualRow(slug, entry);
      onEntered();
      onClose();
    } catch (error) {
      // the server names the field where it can, and the reason where the
      // refusal belongs to no single field
      const fields = apiErrors(error);
      if (fields.length > 0) applyApiErrors(fields);
      else setRefusal(refusalText(t, error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t("manualEntry.title")}</h2>
        <div className="form-fields">
          <label className="form-field">
            <span>{t("column.name")}</span>
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                clearIfValid("name", checkName);
              }}
              onBlur={() => touch("name", checkName)}
              {...invalidProps("name", errors.name)}
            />
            <FieldError field="name" error={errors.name} />
          </label>

          <label className="form-field">
            <span>{t("column.nationality")}</span>
            <input
              value={nationality}
              onChange={(event) => {
                setNationality(event.target.value);
                clearIfValid("nationality", checkNationality);
              }}
              onBlur={() => touch("nationality", checkNationality)}
              {...invalidProps("nationality", errors.nationality)}
            />
            <FieldError field="nationality" error={errors.nationality} />
          </label>

          <label className="form-field">
            <span>{t("column.club")}</span>
            <input
              value={club}
              onChange={(event) => {
                setClub(event.target.value);
                clearIfValid("club", checkClub);
              }}
              onBlur={() => touch("club", checkClub)}
              {...invalidProps("club", errors.club)}
            />
            <FieldError field="club" error={errors.club} />
          </label>

          <label className="form-field">
            <span>{t("column.hr_id")}</span>
            <input
              value={hrId}
              onChange={(event) => {
                setHrId(event.target.value);
                clearIfValid("hr_id", checkHrId);
              }}
              onBlur={() => touch("hr_id", checkHrId)}
              {...invalidProps("hr_id", errors.hr_id)}
            />
            <FieldError field="hr_id" error={errors.hr_id} />
          </label>

          <label className="form-field">
            <span>{t("manualEntry.email")}</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              {...invalidProps("email", errors.email)}
            />
            <FieldError field="email" error={errors.email} />
          </label>

          <label className="form-field">
            <span>{t("column.registered_at")}</span>
            {/* the tournament's own clock, so a form received last week is
                entered with the moment it was received */}
            <input
              type="datetime-local"
              value={registeredAt}
              onChange={(event) => setRegisteredAt(event.target.value)}
              {...invalidProps("registered_at", errors.registered_at)}
            />
            <FieldError field="registered_at" error={errors.registered_at} />
          </label>

          <fieldset className="form-field">
            <legend>{t("column.disciplines")}</legend>
            {offered.map((discipline) => (
              <label key={discipline.slug} className="checkbox-chip">
                <input
                  type="checkbox"
                  checked={disciplines.includes(discipline.slug)}
                  onChange={() => toggle(disciplines, discipline.slug, setDisciplines)}
                />
                <span>{discipline.name}</span>
              </label>
            ))}
          </fieldset>

          {lent.length > 0 && (
            <fieldset className="form-field">
              <legend>{t("column.weapon_rentals")}</legend>
              {lent.map((item) => (
                <label key={item.id} className="checkbox-chip">
                  <input
                    type="checkbox"
                    checked={rentals.includes(item.name)}
                    onChange={() => toggle(rentals, item.name, setRentals)}
                  />
                  <span>{item.name}</span>
                </label>
              ))}
            </fieldset>
          )}

          {holdsAfterparty && (
            <label className="checkbox-chip">
              <input
                type="checkbox"
                checked={afterparty}
                onChange={(event) => setAfterparty(event.target.checked)}
              />
              <span>{t("column.afterparty")}</span>
            </label>
          )}

          <label className="form-field">
            <span>{t("column.notes")}</span>
            <textarea
              value={notes}
              rows={3}
              onChange={(event) => {
                setNotes(event.target.value);
                clearIfValid("notes", checkNotes);
              }}
              onBlur={() => touch("notes", checkNotes)}
              {...invalidProps("notes", errors.notes)}
            />
            <FieldError field="notes" error={errors.notes} />
          </label>
        </div>

        {refusal && <p className="login-error">{refusal}</p>}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={submit}>
            {busy ? t("common.loading") : t("manualEntry.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

/** The server's own refusals, in the organizer's words. A detail this does not
 *  know is reported as a plain refusal rather than as its own wire text. */
function refusalText(t: (key: string) => string, error: unknown): string {
  const detail = (error as { detail?: unknown })?.detail;
  if (typeof detail === "string") {
    return t(`manualEntry.refusal.${detail}`);
  }
  if (detail && typeof detail === "object") {
    const [reason] = Object.keys(detail as Record<string, unknown>);
    if (reason) return t(`manualEntry.refusal.${reason}`);
  }
  return t("manualEntry.refusal.failed");
}
