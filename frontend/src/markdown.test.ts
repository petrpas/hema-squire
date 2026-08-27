// @vitest-environment jsdom
// The sanitizer needs a document; the other suites stay on the node environment.
import { describe, expect, it } from "vitest";

import { renderInline } from "./markdown";

const OSM = "https://osm.org/go/0J0ajlLg8?m=";

describe("renderInline", () => {
  it("renders a link as a link", () => {
    const html = renderInline(`[ZŠ Bílá](${OSM})`);
    expect(html).toContain(`href="${OSM}"`);
    expect(html).toContain("ZŠ Bílá");
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).not.toContain("[");
  });

  it("keeps only the label when links are not allowed", () => {
    expect(renderInline(`[ZŠ Bílá](${OSM})`, { links: false })).toBe("ZŠ Bílá");
  });

  it("renders the rest of the inline subset", () => {
    expect(renderInline("**Praha**")).toBe("<strong>Praha</strong>");
    expect(renderInline("*Praha*")).toBe("<em>Praha</em>");
    expect(renderInline("`Praha`")).toBe("<code>Praha</code>");
    expect(renderInline("~~Praha~~")).toBe("<del>Praha</del>");
  });

  it("leaves emphasis intact when links are not allowed", () => {
    expect(renderInline("**Praha**", { links: false })).toBe("<strong>Praha</strong>");
  });

  it("leaves block syntax literal", () => {
    expect(renderInline("# Praha")).toBe("# Praha");
    expect(renderInline("- Praha")).toBe("- Praha");
    expect(renderInline("> Praha")).toBe("&gt; Praha");
    expect(renderInline("| a | b |")).not.toContain("<table");
  });

  it("never introduces a block element or a line break", () => {
    for (const src of ["# Praha", "- Praha", "1. Praha", "---", "| a | b |"]) {
      expect(renderInline(src)).not.toMatch(/<(p|br|ul|ol|li|h[1-6]|hr|table|blockquote)\b/);
    }
  });

  it("cannot inject markup", () => {
    expect(renderInline("<script>alert(1)</script>")).not.toContain("<script");
    expect(renderInline("<img src=x onerror=alert(1)>")).not.toContain("<img");
    expect(renderInline("<iframe src=x></iframe>")).not.toContain("<iframe");
    const link = renderInline("[click](javascript:alert(1))");
    expect(link).not.toContain("javascript:");
    expect(link).toContain("click");
  });

  it("keeps a plain-text location exactly as written", () => {
    expect(renderInline("Sportovní hala, Praha 6")).toBe("Sportovní hala, Praha 6");
    expect(renderInline("Hala U Sokola (vchod z ulice Bílá)")).toBe(
      "Hala U Sokola (vchod z ulice Bílá)",
    );
  });

  it("produces nothing for an empty or blank source", () => {
    expect(renderInline("")).toBe("");
    expect(renderInline("   ").trim()).toBe("");
  });
});
