import type { useSuggestions } from "./useSuggestions";

/** The values a Setup field recalls, listed beneath it. Static, on the
 *  `HelpHint` box's treatment: `--paper-raised` under a 1px `--ink` rule at the
 *  2px radius, with no shadow, no blur and no entrance animation (design D3).
 *  Renders nothing at all when there is nothing to offer. */
export default function SuggestionList({
  suggestions,
  label,
}: {
  suggestions: ReturnType<typeof useSuggestions>;
  label: string;
}) {
  if (!suggestions.visible) return null;

  return (
    <ul className="suggestion-list" id={suggestions.listId} role="listbox" aria-label={label}>
      {suggestions.matches.map((entry, index) => (
        <li
          key={`${entry.value} ${entry.secondary ?? ""}`}
          id={`${suggestions.listId}-${index}`}
          role="option"
          aria-selected={index === suggestions.active}
          className={
            index === suggestions.active ? "suggestion-option is-active" : "suggestion-option"
          }
          // cancelled so the click lands on the option before the input's blur
          // can take the list away
          onMouseDown={(event) => {
            event.preventDefault();
            suggestions.choose(index);
          }}
        >
          <span className="suggestion-value">{entry.value}</span>
          {entry.secondary && <span className="suggestion-secondary">{entry.secondary}</span>}
        </li>
      ))}
    </ul>
  );
}
