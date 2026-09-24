import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import Modal from "../Modal";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkUrl, type FieldError as FieldErrorValue } from "../validation";
import ServiceAccountStep from "./ServiceAccountStep";

/** Where the Sheets export writes, as the three things that have to be true
 *  for it to succeed rather than as a bare address field. It opens from an
 *  export pressed with no destination stored, and from nowhere else.
 *
 *  The field on its own was the old shape, and it sat in Setup two tabs from
 *  the button that used it. What it never stated is the step that actually
 *  decides whether an export works: the spreadsheet must be shared for writing
 *  with the service account, which is an identity of its own. Stating the three
 *  steps in order is the whole point of the dialog.
 *
 *  `onSaved` is how the export button gets its press back. A wizard the button
 *  opened runs the export once the address is stored, so the organizer's press
 *  is honoured rather than swallowed by a dialog. */
export default function SheetWizard({
  slug,
  account,
  onSaved,
  onClose,
}: {
  slug: string;
  account: string;
  onSaved: (url: string) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();

  function check(): FieldErrorValue | null {
    return checkUrl("output_sheet_url", "TournamentUpdate.output_sheet_url", value);
  }

  async function confirm() {
    // `validateAll` answers with how many fields are wrong, so zero is the
    // case that proceeds.
    if (validation.validateAll([check]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateTournament(slug, { output_sheet_url: value });
      onSaved(value);
    } catch (failure) {
      // Reported in place rather than closing on it: the organizer has just
      // followed three steps, and a dialog that vanishes on failure takes the
      // address they pasted with it.
      const fields = apiErrors(failure);
      validation.applyApiErrors(fields);
      setError(
        fields.length > 0
          ? fields.map((field) => t(`validation.${field.code}`, field.params)).join(" ")
          : t("setup.saveBar.genericError", {
              status: failure instanceof ApiError ? failure.status : "?",
            }),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("export.wizard.title")}</h2>
        <ol className="wizard-steps">
          <li>
            <p>{t("export.wizard.create")}</p>
          </li>
          <ServiceAccountStep account={account} />
          <li>
            <p>{t("export.wizard.paste")}</p>
            <label className="form-field">
              <input
                // The organizer arrives here having just copied a link; the
                // field is what they came for.
                autoFocus
                type="text"
                value={value}
                onChange={(event) => {
                  setValue(event.target.value);
                  validation.clearIfValid("output_sheet_url", check);
                }}
                onBlur={() => validation.touch("output_sheet_url", check)}
                {...invalidProps("output_sheet_url", validation.errors.output_sheet_url)}
              />
              <FieldError field="output_sheet_url" error={validation.errors.output_sheet_url} />
            </label>
          </li>
        </ol>
        {error && <p className="login-error">{error}</p>}
        {/* Cancel first, the committing action second and filled, as every
            other dialog in the app writes its actions. */}
        <div className="modal-actions wizard-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => void confirm()}
          >
            {/* named after what it goes on to do: the organizer pressed
                export, and is owed the word they pressed */}
            {busy ? t("common.loading") : t("export.wizard.confirmExport")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
