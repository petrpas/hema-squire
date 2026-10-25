import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useOutletContext } from "react-router-dom";
import { api, setToken } from "./api";
import type { FencerOutletContext } from "./FencerHome";
import { home, readReturn } from "./routes";
import { credentialChanged } from "./session";

/** Finishing a signup: the link's key is presented once, the account comes
 *  into existence, and the fencer is signed in where the signup was started
 *  (spec `fencer-accounts`, An account exists only once its address is
 *  verified). A link that no longer works is stated, not reported as an
 *  error. */
export default function VerifyScreen() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { onSignIn, resumeAt } = useOutletContext<FencerOutletContext>();
  const [invalid, setInvalid] = useState(false);
  // A key works once. Development's double-mounted effect would otherwise
  // spend it on the first run and report the second as a dead link.
  const presented = useRef(false);
  const key = location.hash.slice(1);

  useEffect(() => {
    if (presented.current) return;
    presented.current = true;
    if (key === "") {
      setInvalid(true);
      return;
    }
    api.verify(key).then(
      ({ token, return_to }) => {
        setToken(token);
        credentialChanged();
        const target = return_to === null ? null : readReturn(return_to);
        if (target?.registration) resumeAt("registration");
        navigate(target?.path ?? home(), { replace: true });
      },
      () => setInvalid(true),
    );
  }, [key, navigate, resumeAt]);

  if (!invalid) return <p>{t("common.loading")}</p>;

  return (
    <div className="workspace">
      <section className="rail-card dashed verify-invalid">
        <p className="rail-hint">{t("verify.invalid")}</p>
        <div className="action-pair">
          <button type="button" className="secondary" onClick={() => onSignIn()}>
            {t("login.submit")}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => onSignIn(undefined, undefined, "signup")}
          >
            {t("login.createAccount")}
          </button>
        </div>
      </section>
    </div>
  );
}
