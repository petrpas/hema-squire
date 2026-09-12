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
