import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type HRProfile, type SheetRow, type SubstituteIn } from "../api";
import Modal from "../Modal";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString } from "../validation";
import SubstituteContactSection from "./SubstituteContactSection";
import SubstituteIdentitySection from "./SubstituteIdentitySection";

/** A seat handed on: the row keeps its number, its order, its symbol, its
 *  totals and everything credited against it, and only the person changes
 *  (spec `fencer-substitution`, A seat may change hands).
 *
 *  Entered whole or not at all, which is why it is a dialog and not an editable
 *  name cell: a substitution is a name, a profile, an address and a notice
 *  about mail taken together. Acceptance is the server's to decide — the checks
 *  here spare a round trip for what the client can see, and a refusal the
 *  client could not predict is rendered against the field the server names. */
export default function SubstituteDialog({
  slug,
  row,
  automatic,
  onSubstituted,
  onClose,
}: {
  slug: string;
  row: SheetRow;
  /** Whether Squire keeps this tournament's registrations. It decides whether
   *  an address is required and whether anything is said about mail. */
  automatic: boolean;
  onSubstituted: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { errors, touch, validateAll, applyApiErrors } = useFieldValidation();
  const current = row.email ?? null;
  const [name, setName] = useState("");
  const [profile, setProfile] = useState<HRProfile | null>(null);
  // The ordinary case is that the substitute has their own address; keeping
  // the seat's is the exception, and an exception is not a default.
  const [keeping, setKeeping] = useState(false);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [refusal, setRefusal] = useState<string | null>(null);

  const checkName = () => checkString("name", "SubstituteIn.name", name, { required: true });
  const checkEmail = () => checkString("email", "SubstituteIn.email", email);

  function chosen(picked: HRProfile | null) {
    setProfile(picked);
    // the canonical spelling is what the row will carry, so it is what the
    // organizer sees the moment they pick it
    if (picked !== null) setName(picked.name);
  }

  const address = keeping && current !== null ? current : email.trim();

  async function submit() {
    setRefusal(null);
    if (validateAll([checkName, checkEmail]) > 0) return;
    if (automatic && address === "") {
      setRefusal(t("substitute.refusal.substitute_email_required"));
      return;
    }
    const substitute: SubstituteIn = {
      name: name.trim(),
      hr_id: profile?.hr_id ?? null,
      nationality: profile?.nationality ?? null,
      club: profile?.club ?? null,
      email: address === "" ? null : address,
    };
    setBusy(true);
    try {
      await api.substituteFencer(slug, row.id, substitute);
      onSubstituted();
      onClose();
    } catch (error) {
      const fields = apiErrors(error);
      if (fields.length > 0) applyApiErrors(fields);
      else setRefusal(refusalText(t, error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("substitute.title")}</h2>
        <p className="rail-hint">{t("substitute.replacing", { name: row.name })}</p>
        <div className="form-fields">
          <SubstituteIdentitySection
            name={name}
            onName={setName}
            profile={profile}
            onProfile={chosen}
            error={errors.name}
            onBlur={() => touch("name", checkName)}
          />
          <SubstituteContactSection
            automatic={automatic}
            current={current}
            keeping={keeping}
            onKeeping={setKeeping}
            email={email}
            onEmail={setEmail}
            error={errors.email}
            onBlur={() => touch("email", checkEmail)}
          />
        </div>

        {refusal && <p className="login-error">{refusal}</p>}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={submit}>
            {busy ? t("common.loading") : t("substitute.submit")}
          </button>
        </div>
      </div>
    </Modal>
  );
}

/** The server's own refusals, in the organizer's words. A detail this does not
 *  know is reported as a plain refusal rather than as its own wire text. */
function refusalText(t: (key: string) => string, error: unknown): string {
  const detail = (error as { detail?: unknown })?.detail;
  if (typeof detail === "string") return t(`substitute.refusal.${detail}`);
  if (detail && typeof detail === "object") {
    const [reason] = Object.keys(detail as Record<string, unknown>);
    if (reason) return t(`substitute.refusal.${reason}`);
  }
  return t("substitute.refusal.failed");
}
