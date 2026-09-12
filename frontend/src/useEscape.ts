import { useEffect } from "react";

/** Escape dismisses whatever is open over the page. A screen that stands in
 *  front of what the visitor was reading — the sign-in form over a public
 *  page, the signup form over sign-in — has to hear it too, not only a
 *  `<dialog>`, which gets it from the element itself.
 *
 *  Pass `null` where there is nothing to leave to: the listener is not
 *  attached at all then, so a screen with no way back does not silently
 *  swallow the key. */
export default function useEscape(onEscape: (() => void) | null): void {
  useEffect(() => {
    if (onEscape === null) return;
    function dismiss(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onEscape?.();
    }
    document.addEventListener("keydown", dismiss);
    return () => document.removeEventListener("keydown", dismiss);
  }, [onEscape]);
}
