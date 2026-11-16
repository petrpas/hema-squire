import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError, api, setToken } from "./api";
import { profile } from "./routes";
import { credentialChanged } from "./session";

type State =
  | { kind: "loading" }
  | { kind: "ready"; email: string }
  | { kind: "invalid" }
  | { kind: "taken" };

/** Following an address-change link (spec `profile-page`, Address change).
 *
 *  The key is inspected first, consuming nothing, and the change is made only
 *  when the reader confirms it: a mail scanner opening the link changes no
 *  address. Confirming ends every earlier session and signs this browser in,
 *  as a reset does, then lands on the Profile page. A dead link and an
 *  address taken meanwhile are stated, not reported as errors. */
export default function ConfirmEmail() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const key = location.hash.slice(1);
  const [state, setState] = useState<State>({ kind: "loading" });
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (key === "") {
      setState({ kind: "invalid" });
      return;
    }
    api.inspectEmailChange(key).then(
      (it) => setState({ kind: "ready", email: it.email }),
      () => setState({ kind: "invalid" }),
    );
  }, [key]);

  async function confirm() {
    setBusy(true);
    setFailed(false);
    try {
      const { token } = await api.confirmEmailChange(key);
      setToken(token);
      credentialChanged();
      navigate(profile(), { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 410) setState({ kind: "invalid" });
      else if (err instanceof ApiError && err.status === 409) setState({ kind: "taken" });
      else setFailed(true);
      setBusy(false);
    }
  }

  if (state.kind === "loading") return <p>{t("common.loading")}</p>;

  if (state.kind !== "ready") {
    return (
      <div className="workspace">
        <section className="rail-card dashed email-confirm-dead">
          <p className="rail-hint">
            {t(state.kind === "taken" ? "confirmEmail.taken" : "confirmEmail.invalid")}
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="workspace">
      <section className="rail-card email-confirm">
        <h2>{t("confirmEmail.title")}</h2>
        <p className="rail-hint">{t("confirmEmail.meaning", { email: state.email })}</p>
        {failed && <p className="login-error">{t("confirmEmail.failed")}</p>}
        <button
          type="button"
          className="btn-primary"
          disabled={busy}
          onClick={() => void confirm()}
        >
          {busy ? t("confirmEmail.confirming") : t("confirmEmail.confirm")}
        </button>
      </section>
    </div>
  );
}
