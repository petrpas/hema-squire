import { Marked } from "marked";
import DOMPurify from "dompurify";

// Organizers naturally start a document at `#`; demoting rather than dropping
// keeps their structure while guaranteeing rendered prose never out-shouts the
// screen's own document heading (`--font-doc`).
const marked = new Marked({
  gfm: true,
  breaks: true,
  async: false,
  renderer: {
    heading({ tokens, depth }) {
      const level = depth <= 3 ? 3 : 4;
      return `<h${level}>${this.parser.parseInline(tokens)}</h${level}>\n`;
    },
  },
});

// The inline tags are the whole vocabulary of a one-line field; the block tags
// are what long-form prose adds on top. Written as base + block rather than as
// two literal lists so the two allowlists cannot drift apart.
const INLINE_TAGS = ["strong", "em", "del", "code", "a"];
const BLOCK_TAGS = ["p", "br", "ul", "ol", "li", "h3", "h4", "blockquote", "pre", "hr"];
const ALLOWED_TAGS = [...INLINE_TAGS, ...BLOCK_TAGS];
const ALLOWED_ATTR = ["href"];
const ALLOWED_URI_REGEXP = /^(https?:|mailto:|#)/i;

// Registered once at module load: target/rel are never in ALLOWED_ATTR, so an
// organizer cannot inject them — these values are ours, applied after sanitization.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A" && node.getAttribute("href")?.[0] !== "#") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

/** The single entry point for turning organizer-authored markdown into safe HTML. */
export function renderMarkdown(src: string): string {
  const html = marked.parse(src, { async: false }) as string;
  return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR, ALLOWED_URI_REGEXP });
}

/**
 * The same for a field that has to stay on one line. `parseInline` tokenizes the
 * source as inline content, so a heading or a list is never a token to begin
 * with and comes out as the characters the organizer typed — no block markup to
 * strip and no `breaks` line break to suppress.
 *
 * `links: false` is for a field rendered inside a region that is itself a link:
 * dropping `a` from the allowlist leaves DOMPurify to keep the anchor's own text,
 * so the label survives and no link is ever nested inside another.
 */
export function renderInline(src: string, { links = true }: { links?: boolean } = {}): string {
  const html = marked.parseInline(src, { async: false }) as string;
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: links ? INLINE_TAGS : INLINE_TAGS.filter((tag) => tag !== "a"),
    ALLOWED_ATTR,
    ALLOWED_URI_REGEXP,
  });
}
