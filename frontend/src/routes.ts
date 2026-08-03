import type { Phase } from "./Console";
import type { HomeTab } from "./FencerShell";

export function home(tab?: HomeTab): string {
  return tab && tab !== "open" ? `/?tab=${tab}` : "/";
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
