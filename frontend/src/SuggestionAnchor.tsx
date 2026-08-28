import type { ReactNode } from "react";

/** Positioning context for a suggestion list, wrapped around the input it hangs
 *  from. `active` is false for fields that do not recall prior values, and those
 *  keep their markup exactly as it was — a section that renders its fields from
 *  one shared function should not grow a wrapper around all of them to give one
 *  of them a list. */
export default function SuggestionAnchor({
  active,
  children,
}: {
  active: boolean;
  children: ReactNode;
}) {
  if (!active) return <>{children}</>;
  return <span className="suggestion-anchor">{children}</span>;
}
