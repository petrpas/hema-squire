import { useEffect, useMemo, useRef, useState } from "react";

import type { TournamentDetail } from "./api";
import {
  COUNTDOWN_WINDOW_MS,
  correctedNow,
  openingMomentMs,
  serverSkewMs,
  withinCountdownWindow,
} from "./openingMoment";

/** A margin on the scheduled unlock, so a timer that fires a hair early does
 *  not re-render the page into a state the server still refuses. */
const UNLOCK_MARGIN_MS = 500;

export interface OpeningMoment {
  /** The server's clock as best this device can tell — what every "now"
   *  comparison on the page is made against, rather than `Date.now()`. */
  now: number;
  /** The opening instant, or null when the tournament opens on publication. */
  opensAt: number | null;
  /** Milliseconds left until it, or null when there is no moment to wait for.
   *  Never negative: it stops at zero. */
  remainingMs: number | null;
  /** Whether a countdown belongs on the page — only inside the last day. */
  counting: boolean;
}

/** Watches the moment registration opens and re-renders the page through it.
 *
 *  It costs no requests while it waits: a single timeout is scheduled for the
 *  opening instant (a thousand fencers holding the page open must not become a
 *  thousand requests a second), and `onOpen` fires once when it arrives so the
 *  page can refresh seat counts that are stale by then. A backgrounded tab
 *  throttles timers and a sleeping device suspends them, so the same check
 *  runs again whenever the page is looked at (design D8).
 *
 *  `onOpen` fires on the *transition* alone — never on a page that was already
 *  open when it loaded, and never again on the payload its own refresh brings
 *  back. Both would be loops, and both cost exactly what the single scheduled
 *  timeout exists to avoid.
 *
 *  Inside the last day it also ticks once a second, which is what re-renders
 *  the countdown figure. Outside it nothing ticks until the window opens. */
export function useOpeningMoment(
  detail: TournamentDetail | null,
  onOpen: () => void,
): OpeningMoment {
  // measured once per payload: a re-render must not re-measure against a
  // device clock that has drifted since. Held in a ref as well, so the
  // scheduling effect can read it without being re-run by it — the skew is a
  // correction, not a trigger
  const skew = useMemo(() => (detail ? serverSkewMs(detail.server_time) : 0), [detail]);
  const skewRef = useRef(skew);
  skewRef.current = skew;

  const opensAt = useMemo(
    () => (detail ? openingMomentMs(detail.registration_opens_at) : null),
    [detail],
  );

  const [now, setNow] = useState(() => correctedNow(skew));
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  // whether there is a transition still to come: set only where the moment is
  // genuinely ahead of us. A page that loaded after the opening is not armed,
  // so it never asks for the refresh it does not need
  const armed = useRef(false);
  useEffect(() => {
    armed.current = opensAt !== null && correctedNow(skewRef.current) < opensAt;
  }, [opensAt]);

  const remainingMs = opensAt === null ? null : Math.max(0, opensAt - now);
  const counting = remainingMs !== null && withinCountdownWindow(remainingMs);

  useEffect(() => {
    if (opensAt === null) return;

    function check() {
      const current = correctedNow(skewRef.current);
      setNow(current);
      if (current >= (opensAt as number) && armed.current) {
        // the transition, once: the guard is not re-armed by the payload this
        // refresh brings back
        armed.current = false;
        onOpenRef.current();
      }
    }

    const remaining = opensAt - correctedNow(skewRef.current);
    if (remaining <= 0) {
      check();
      return;
    }

    // one timeout for the moment itself; a second-by-second tick only while a
    // countdown is on show, and otherwise a single coarse timer that wakes the
    // page when the last day begins
    const unlock = window.setTimeout(check, remaining + UNLOCK_MARGIN_MS);
    const tick = counting ? window.setInterval(check, 1000) : undefined;
    const enterWindow =
      !counting && remaining > COUNTDOWN_WINDOW_MS
        ? window.setTimeout(check, remaining - COUNTDOWN_WINDOW_MS)
        : undefined;
    // a throttled or suspended timer misses the moment; looking at the page
    // again is the other signal that it may have passed
    const onVisible = () => {
      if (document.visibilityState === "visible") check();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", check);

    return () => {
      window.clearTimeout(unlock);
      if (tick !== undefined) window.clearInterval(tick);
      if (enterWindow !== undefined) window.clearTimeout(enterWindow);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", check);
    };
  }, [opensAt, counting]);

  return { now, opensAt, remainingMs, counting };
}
