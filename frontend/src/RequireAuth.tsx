import { useEffect, useState } from "react";
import { Outlet, useNavigate, useOutletContext } from "react-router-dom";

import Login from "./Login";
import { api, getToken, setToken } from "./api";
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
    if (authed) {
      api.account().then((account) => void i18n.changeLanguage(account.language), () => {});
    }
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
