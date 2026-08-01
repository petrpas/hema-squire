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

const ALLOWED_TAGS = [
  "p", "br", "strong", "em", "del", "ul", "ol", "li",
  "h3", "h4", "a", "blockquote", "code", "pre", "hr",
];
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
