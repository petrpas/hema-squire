import { useEffect, useState } from "react";
import { Outlet, useNavigate, useOutletContext } from "react-router-dom";

import Login from "./Login";
import { ApiError, api, getToken, setToken } from "./api";
import i18n from "./i18n";

type AuthContext = { onLogout: () => void };

export function useAuth(): AuthContext {
  return useOutletContext<AuthContext>();
}

/** The auth gate: renders Login in place at the requested URL when signed
 *  out, so the destination and its query string survive login with no
 *  history entry pushed (design D7). */
export default function RequireAuth() {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(() => getToken() !== null);

  useEffect(() => {
    if (!authed) return;
    api.account().then(
      (account) => void i18n.changeLanguage(account.language),
      (err) => {
        // A stored token is not proof of a session. On a phone it is typically
        // weeks old, and holding the shell open on the strength of its mere
        // presence produced a signed-in page with a blank identity and an
        // empty list — which reads as a broken app, not as being signed out.
        //
        // Only a rejection discards it. Every other failure — offline, DNS, a
        // 502 — is left alone: those resolve themselves, and ending a session
        // over one loses the fencer's place for a reason that was never about
        // their credential.
        //
        // No navigation here: RequireAuth renders Login in place, so the
        // expiry costs the session and not the destination as well (spec
        // routing: "Unauthenticated visits keep their destination").
        if (err instanceof ApiError && err.status === 401) {
          setToken(null);
          setAuthed(false);
        }
      },
    );
  }, [authed]);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  function onLogout() {
    setToken(null);
    setAuthed(false);
    navigate("/", { replace: true });
  }

  return <Outlet context={{ onLogout } satisfies AuthContext} />;
}
