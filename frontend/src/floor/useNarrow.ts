import { useSyncExternalStore } from "react";

/** The canonical middle breakpoint (tokens.css), written as the CSS writes it,
 *  so both agree on which side 768px itself falls. */
const NARROW = "(max-width: 768px)";

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

/** Whether the floor console is below the canonical breakpoint, followed live
 *  as the window is resized: there the schedule panel becomes the last tab
 *  (spec floor-console, A schedule panel stands beside the work). Where
 *  `matchMedia` is unavailable (jsdom) the answer is "wide". */
export function useNarrow(): boolean {
  return useSyncExternalStore(subscribe, () => query()?.matches ?? false);
}
