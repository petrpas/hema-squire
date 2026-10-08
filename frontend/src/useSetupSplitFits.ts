import { useSyncExternalStore } from "react";

/** The width at or below which Setup's preview no longer fits beside the
 *  settings and moves into its own tab. It is the same number as the 1300px
 *  block of index.css — a content threshold, not a device breakpoint (see
 *  tokens.css) — and the two must change together. Written as `max-width`,
 *  like the CSS, so both agree on which side the threshold itself falls. */
const NARROW = "(max-width: 1300px)";

function query(): MediaQueryList | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(NARROW)
    : null;
}

function subscribe(onChange: () => void): () => void {
  const list = query();
  list?.addEventListener("change", onChange);
  return () => list?.removeEventListener("change", onChange);
}

/** Whether the Setup preview fits beside the settings, followed live as the
 *  window is resized — unlike `useWideViewport`, which reads once on purpose.
 *  Where `matchMedia` is unavailable (jsdom) the answer is "fits", the layout
 *  every test written before the preview tab assumes. */
export function useSetupSplitFits(): boolean {
  return useSyncExternalStore(subscribe, () => !(query()?.matches ?? false));
}
