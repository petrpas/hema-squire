import { useMemo } from "react";
import { renderInline } from "./markdown";

/**
 * The one-line sibling of `Prose`: renders an inline markdown field as a `<span>`
 * so it can sit on a shared line — a middle-dot fact line, a card's date and
 * place — without a block wrapper. Like `Prose`, it reaches the DOM only through
 * the sanitizer in `markdown.ts`.
 *
 * `links={false}` where the surrounding region is itself a link: the destination
 * is dropped and the label stays, so no link is ever nested inside another.
 */
export default function InlineProse({
  source,
  links = true,
  className,
}: {
  source?: string | null;
  links?: boolean;
  className?: string;
}) {
  const html = useMemo(
    () => (source && source.trim() ? renderInline(source, { links }) : ""),
    [source, links],
  );
  if (!html) return null;
  return (
    <span
      className={["prose-inline", className].filter(Boolean).join(" ")}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
