import { useId, useState } from "react";

import { filterSuggestions, type SuggestionEntry, worthOffering } from "./suggestions";

/** Keyboard and open/close state for a field that recalls previously used
 *  values. The field's own input stays where it is — the section keeps
 *  ownership of its value, its validation and its dirty flag — and this hook
 *  supplies the props that turn that input into a combobox, plus the state the
 *  list renders from.
 *
 *  Nothing is ever filled in on the organizer's behalf: `onChoose` fires only
 *  from a deliberate Enter or click. */
export function useSuggestions(
  candidates: SuggestionEntry[],
  query: string,
  onChoose: (entry: SuggestionEntry, index: number) => void,
) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const matches = filterSuggestions(candidates, query);
  // an empty match set renders nothing at all, so a field with no history is
  // indistinguishable from a field that never had the affordance
  const visible = open && worthOffering(matches, query);

  function close() {
    setOpen(false);
    setActive(-1);
  }

  function choose(index: number) {
    const entry = matches[index];
    if (!entry) return;
    onChoose(entry, candidates.indexOf(entry));
    close();
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      // dismissing leaves the typed text exactly as it was; the stop keeps a
      // dismissal from also closing whatever dialog the field sits in
      if (visible) event.stopPropagation();
      close();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!visible) {
        setOpen(true);
        setActive(0);
        return;
      }
      const step = event.key === "ArrowDown" ? 1 : -1;
      const next = active + step;
      setActive(next < 0 ? matches.length - 1 : next >= matches.length ? 0 : next);
      return;
    }
    if (event.key === "Enter" && visible && active >= 0) {
      // only a highlighted entry is taken; Enter on typed text behaves as ever
      event.preventDefault();
      choose(active);
    }
  }

  return {
    matches,
    visible,
    active,
    listId,
    choose,
    close,
    /** spread onto the field's input, alongside its existing handlers */
    inputProps: {
      role: "combobox" as const,
      "aria-expanded": visible,
      "aria-controls": listId,
      "aria-autocomplete": "list" as const,
      "aria-activedescendant": visible && active >= 0 ? `${listId}-${active}` : undefined,
      autoComplete: "off",
      onKeyDown,
      onFocus: () => setOpen(true),
    },
  };
}
