import { useEffect } from "react";
import { Outlet, useNavigate, useOutletContext } from "react-router-dom";
import { ApiError, api } from "./api";
import i18n from "./i18n";
import Login from "./Login";
import { home } from "./routes";
import { credentialChanged, signOut, useCredential, useSignOut } from "./session";

type AuthContext = { onLogout: () => void };

export function useAuth(): AuthContext {
  return useOutletContext<AuthContext>();
}

/** The auth gate: renders Login in place at the requested URL when signed
 *  out, so the destination and its query string survive login with no
 *  history entry pushed (design D7). */
export default function RequireAuth() {
  const authed = useCredential() !== null;
  const onLogout = useSignOut();
  const navigate = useNavigate();

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
          signOut();
        }
      },
    );
  }, [authed]);

  if (!authed) {
    /* Nothing of this destination is readable without an account, so
       declining leads to the public list rather than back to a blank gate. */
    return <Login onLogin={credentialChanged} onCancel={() => navigate(home())} />;
  }

  return <Outlet context={{ onLogout } satisfies AuthContext} />;
}
