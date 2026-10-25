import { useTranslation } from "react-i18next";
import type { HRProfile } from "./api";
import HRSearchPicker from "./HRSearch";
import HRSearchStep from "./HRSearchStep";
import { useWideViewport } from "./useWideViewport";

/** The account form's optional HEMA Ratings step: the search, the ownership
 *  confirmation, and the line a confirmed profile leaves behind. One step for
 *  both variants of the form, since the guest variant's binding is the same
 *  explicit claim (spec `fencer-accounts`). The state stays with the form,
 *  whose Escape unwinds it. */
export default function SignupHrStep({
  name,
  hrProfile,
  pendingHr,
  showHrSearch,
  onPick,
  onConfirm,
  onClear,
  onShowSearch,
}: {
  name: string;
  hrProfile: HRProfile | null;
  /** a candidate picked but not yet confirmed as the signer's own */
  pendingHr: HRProfile | null;
  showHrSearch: boolean;
  onPick: (profile: HRProfile | null) => void;
  onConfirm: (profile: HRProfile) => void;
  onClear: () => void;
  onShowSearch: (shown: boolean) => void;
}) {
  const { t } = useTranslation();
  const wide = useWideViewport();

  // The HR picker, configured the way signup needs it. Built once here so the
  // inline placement and the full-screen step below cannot drift apart.
  const picker = (
    <HRSearchPicker
      onConfirm={onPick}
      onCancel={() => onShowSearch(false)}
      lockedQuery={name}
      requireNationality
    />
  );

  if (hrProfile) {
    return (
      <p className="signup-hr-confirmed">
        {t("signup.hr.confirmed", { name: hrProfile.name, hrId: hrProfile.hr_id })}{" "}
        <button type="button" className="link-button" onClick={onClear}>
          {t("signup.hr.clear")}
        </button>
        {hrProfile.claimed && (
          <span className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</span>
        )}
      </p>
    );
  }
  if (pendingHr) {
    return (
      <section className="rail-card hr-confirm">
        <h2>{t("signup.hr.confirmTitle")}</h2>
        <p className="hr-confirm-name">{pendingHr.name}</p>
        <p className="muted">
          {pendingHr.club ?? "—"} · {pendingHr.nationality ?? "—"} · #{pendingHr.hr_id}
        </p>
        <a
          className="hr-confirm-link"
          href={`https://hemaratings.com/fighters/details/${pendingHr.hr_id}/`}
          target="_blank"
          rel="noreferrer"
        >
          {t("signup.hr.viewProfile")}
        </a>
        {pendingHr.claimed && <p className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</p>}
        <p className="rail-hint">{t("signup.hr.confirmPrompt")}</p>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => onPick(null)}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" onClick={() => onConfirm(pendingHr)}>
            {t("signup.hr.confirmButton")}
          </button>
        </div>
      </section>
    );
  }
  if (showHrSearch) {
    return wide ? (
      <section className="rail-card">
        <h2>{t("profile.hr.title")}</h2>
        {picker}
      </section>
    ) : (
      /* Rendered here, inside the form's own component tree, so opening the
         step unmounts nothing: e-mail, password, name and language are all
         still held by the form and survive the round trip. A route of its
         own would discard them. */
      <HRSearchStep
        title={t("profile.hr.title")}
        /* The picker is locked to the form's name field and shows no query
           input, so the step has to say what it is searching for. */
        subtitle={t("signup.hr.searchingFor", { name })}
        backLabel={t("signup.hr.stepBack")}
        onBack={() => onShowSearch(false)}
      >
        {picker}
      </HRSearchStep>
    );
  }
  return (
    <button type="button" className="secondary" onClick={() => onShowSearch(true)}>
      {t("signup.hr.find")}
    </button>
  );
}
