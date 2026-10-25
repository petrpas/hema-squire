import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, api, type HRProfile } from "../api";
import HRSearchPicker from "../HRSearch";
import HRSearchStep from "../HRSearchStep";
import useEscape from "../useEscape";
import { useWideViewport } from "../useWideViewport";

export default function HRMatchSection({
  account,
  onBound,
}: {
  account: Account;
  onBound: (account: Account) => void;
}) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<HRProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wide = useWideViewport();
  // below 768px the picker is opened as its own screen rather than sitting
  // expanded in the section
  const [searching, setSearching] = useState(false);
  // Escape leaves the step before it leaves the page: the page's own close
  // stands aside while the step, a modal layer, is open
  useEscape(pending === null && !wide && searching ? () => setSearching(false) : null);

  function select(profile: HRProfile) {
    setPending(profile);
    setError(null);
  }

  async function confirmBinding() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      const account = await api.bindHr(pending.hr_id);
      onBound(account);
    } catch {
      setError(t("profile.hr.bindFailed"));
    } finally {
      setBusy(false);
    }
  }

  const picker = (
    <HRSearchPicker onConfirm={select} busy={busy} initialQuery={account.display_name} />
  );

  return (
    <section className="rail-card">
      <h2>{t("profile.hr.title")}</h2>
      {pending ? (
        <div className="signup-hr-confirmed">
          <p>{t("signup.hr.confirmed", { name: pending.name })}</p>
          {pending.claimed && (
            <span className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</span>
          )}
          {error && <p className="login-error">{error}</p>}
          <button
            type="button"
            className="btn-primary"
            onClick={() => void confirmBinding()}
            disabled={busy}
          >
            {t("profile.hr.confirmBind")}
          </button>
          <button
            type="button"
            className="link-button"
            onClick={() => setPending(null)}
            disabled={busy}
          >
            {t("common.cancel")}
          </button>
        </div>
      ) : wide ? (
        <>
          <p className="rail-hint">{t("profile.hr.unboundHint")}</p>
          {picker}
        </>
      ) : searching ? (
        /* The same step signup uses, not a second implementation of it. The
           two supply different pickers — signup locks the query to its form's
           name field, this one carries its own seeded from the display name —
           and the step passes that difference through rather than flattening
           it. The step's own back control is the way out: this call site
           gives HRSearchPicker no onCancel, so it renders none of its own. */
        <HRSearchStep
          title={t("profile.hr.title")}
          backLabel={t("profile.hr.stepBack")}
          onBack={() => setSearching(false)}
        >
          {picker}
        </HRSearchStep>
      ) : (
        <>
          <p className="rail-hint">{t("profile.hr.unboundHint")}</p>
          <button type="button" className="secondary" onClick={() => setSearching(true)}>
            {t("signup.hr.find")}
          </button>
        </>
      )}
    </section>
  );
}
