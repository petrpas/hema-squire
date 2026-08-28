import type { Organizer, SetupSuggestions } from "./api";

/** One offered value. `value` is what lands in the field when it is chosen and
 *  what the typed text is matched against; `secondary` is shown beneath it —
 *  the organizer's link, where there is one — so two entries sharing a name can
 *  be told apart. */
export interface SuggestionEntry {
  value: string;
  secondary?: string | null;
}

/** The lists arrive from the backend already distinct, ordered most-recent-first
 *  and capped, so nothing here re-orders them. */
export const EMPTY_SUGGESTIONS: SetupSuggestions = {
  locations: [],
  bank_accounts: [],
  organizers: [],
};

export function plainEntries(values: string[]): SuggestionEntry[] {
  return values.map((value) => ({ value }));
}

/** An organizer's name is what fills the field; its link rides along as the
 *  secondary line, which is what distinguishes one club used with two links. */
export function organizerEntries(organizers: Organizer[]): SuggestionEntry[] {
  return organizers.map((organizer) => ({ value: organizer.name, secondary: organizer.link }));
}

/** Case-insensitive substring, not prefix: an organizer typing "shbu" should
 *  find "Spolek SHBU Praha". Diacritics are compared as typed — an organizer
 *  recalling their own club writes it the way they wrote it (design D4).
 *
 *  An empty query offers everything: the list opens on focus with the whole
 *  short history, which is the common case for a field being filled fresh. */
export function filterSuggestions(entries: SuggestionEntry[], query: string): SuggestionEntry[] {
  const needle = query.trim().toLowerCase();
  if (needle === "") return entries;
  return entries.filter((entry) => entry.value.toLowerCase().includes(needle));
}

/** Nothing is offered when the only candidate is what the field already holds —
 *  a list whose single entry restates the current value is noise. */
export function worthOffering(entries: SuggestionEntry[], query: string): boolean {
  if (entries.length === 0) return false;
  return !(entries.length === 1 && entries[0].value === query.trim());
}
