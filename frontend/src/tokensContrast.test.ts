import { describe, expect, it } from "vitest";

import css from "./tokens.css?raw";

// Every pastel's -ink reaches 4.5:1 on its own tint, in both skins (spec
// design-system, Skins; A fourth pastel tint). Read from tokens.css itself,
// so a value changed there is checked where it lives.

const PASTELS = ["seal-green", "file-blue", "form-yellow", "ledger-red"];

function block(selector: string): Map<string, string> {
  const start = css.indexOf(`${selector} {`);
  const body = css.slice(start, css.indexOf("\n}", start));
  const values = new Map<string, string>();
  for (const match of body.matchAll(/--([a-z-]+):\s*(#[0-9a-f]{6})/g)) {
    const [, name, hex] = match;
    if (name && hex) values.set(name, hex);
  }
  return values;
}

function luminance(hex: string): number {
  const channel = (offset: number) => {
    const value = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

function contrast(a: string, b: string): number {
  const [dark, light] = [luminance(a), luminance(b)].sort((x, y) => x - y);
  return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
}

describe.each([
  ["day", ":root"],
  ["night", '[data-skin="night"]'],
])("the %s skin's pastels", (_skin, selector) => {
  const tokens = block(selector);
  it.each(PASTELS)("%s carries legible ink", (pastel) => {
    const tint = tokens.get(pastel);
    const ink = tokens.get(`${pastel}-ink`);
    expect(tint).toBeDefined();
    expect(ink).toBeDefined();
    expect(contrast(tint ?? "", ink ?? "")).toBeGreaterThanOrEqual(4.5);
  });
});
