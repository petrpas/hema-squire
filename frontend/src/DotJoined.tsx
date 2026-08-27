import { Fragment } from "react";

// extra breathing room around inline "·" separators — several sit right
// next to numerals/currency and read as cramped without it
const DOT = "  ·  ";

/** Joins non-empty parts (strings or nodes, e.g. a ruleset link) with `DOT`,
 * rendering nothing when every part is empty. A part is judged before it
 * renders, so a component that returns null for empty input is still a part
 * and still earns a separator — pass `null` in its place, not the element. */
export default function DotJoined({
  parts,
  className = "muted",
}: {
  parts: React.ReactNode[];
  className?: string;
}) {
  const visible = parts.filter(
    (part) => part !== null && part !== undefined && part !== false && part !== "",
  );
  if (visible.length === 0) return null;
  return (
    <span className={className}>
      {visible.map((part, index) => (
        <Fragment key={index}>
          {index > 0 && DOT}
          {part}
        </Fragment>
      ))}
    </span>
  );
}
