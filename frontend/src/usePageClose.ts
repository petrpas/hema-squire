import { useCallback, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { home } from "./routes";

/** Leaving a page reached from the account menu: back to wherever it was
 *  opened from, or to the tournament list where it was reached by its URL and
 *  there is nowhere in this app to go back to. Escape does the same.
 *
 *  Escape is left alone while something is open over the page — a dialog or a
 *  full-screen step answers it itself — and while a field has focus, where the
 *  key belongs to the field and leaving would drop what was being typed. */
export default function usePageClose(): () => void {
  const navigate = useNavigate();
  const location = useLocation();
  // "default" is the key of the entry the app was loaded on: nothing before
  // it belongs to this app, so going back would leave it
  const close = useCallback(() => {
    if (location.key === "default") navigate(home());
    else navigate(-1);
  }, [location.key, navigate]);

  useEffect(() => {
    function dismiss(event: KeyboardEvent) {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable || target.closest("input, textarea, select") !== null)
      )
        return;
      if (document.querySelector('dialog[open], [aria-modal="true"]') !== null) return;
      event.preventDefault();
      close();
    }
    document.addEventListener("keydown", dismiss);
    return () => document.removeEventListener("keydown", dismiss);
  }, [close]);

  return close;
}
