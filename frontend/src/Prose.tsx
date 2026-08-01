import { useMemo } from "react";
import { renderMarkdown } from "./markdown";

/**
 * Renders organizer-authored markdown as sanitized HTML. The only component in
 * the codebase using `dangerouslySetInnerHTML` — every prose field reaches the
 * DOM through here, so the sanitizer in `markdown.ts` is never bypassed.
 */
export default function Prose({
  source,
  className,
}: {
  source?: string | null;
  className?: string;
}) {
  const html = useMemo(() => (source && source.trim() ? renderMarkdown(source) : ""), [source]);
  if (!html) return null;
  return (
    <div className={["prose", className].filter(Boolean).join(" ")} dangerouslySetInnerHTML={{ __html: html }} />
  );
}
