import type { Phase } from "./Console";
import type { HomeTab } from "./FencerShell";

/** The tournament list. A named tab is spelled out; the bare URL means "the
 *  default tab", resolved from what there is to show (spec `fencer-home`).
 *
 *  `open` used to be the exception that resolved to `/`, because `/` *was*
 *  Open. It no longer is: a bare `/` now resolves against the visitor's own
 *  lists, so an Open link that dropped its tab would land wherever that
 *  resolution went. Every tab names itself. */
export function home(tab?: HomeTab): string {
  return tab ? `/?tab=${tab}` : "/";
}

export function detail(slug: string): string {
  return `/t/${slug}`;
}

/** The detail page's Entrants tab, at one discipline's roster or, naming
 *  none, at the first. The one tab of that page with an address of its own,
 *  so a roster can be linked to (spec fencer-home, routing). */
export function entrants(slug: string, discipline?: string): string {
  return discipline ? `/t/${slug}/entrants/${discipline}` : `/t/${slug}/entrants`;
}

/** The Entrants tab at one side event's roster. A segment of its own, so an
 *  event's id can never be read as a discipline's slug. */
export function entrantsEvent(slug: string, item: string): string {
  return `/t/${slug}/entrants/events/${item}`;
}

/** A guest registration's management, its key in the fragment: the browser
 *  sends a fragment to no server and passes it on in no referrer (spec
 *  `guest-registration`, routing). */
export function manage(slug: string, key: string): string {
  return `/t/${slug}/manage#${key}`;
}

/** Finishing a signup, its key in the fragment for the same reason. */
export function verify(key: string): string {
  return `/verify#${key}`;
}

/** A password-reset link, its key in the fragment, which the browser does not
 *  send (spec `password-reset`). The backend builds the same address for the
 *  mail; this is for the screen's own tests and any link to it. */
export function resetPassword(key: string): string {
  return `/reset#${key}`;
}

/** A signup's return path that resumes on the registration tab: what a
 *  verification link carries when the signup was raised by Register, so
 *  following it on another device still lands on the form (design D10). */
export function resumingRegistration(path: string): string {
  return `${path}${REGISTER_MARK}`;
}

/** The return path a verified signup lands on, and whether it was raised by
 *  Register. */
export function readReturn(returnTo: string): { path: string; registration: boolean } {
  return returnTo.endsWith(REGISTER_MARK)
    ? { path: returnTo.slice(0, -REGISTER_MARK.length), registration: true }
    : { path: returnTo, registration: false };
}

const REGISTER_MARK = "#register";

export function picker(): string {
  return "/organizer";
}

export function consolePath(slug: string, phase?: Phase): string {
  return phase ? `/organizer/${slug}/console/${phase}` : `/organizer/${slug}/console`;
}

export function admin(): string {
  return "/admin";
}

export function profile(): string {
  return "/profile";
}
