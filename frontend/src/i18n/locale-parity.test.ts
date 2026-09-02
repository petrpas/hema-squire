import { describe, expect, it } from "vitest";

import { OPERATION_KINDS } from "../api";
import { VALIDATION_CODES } from "../validation";
import cs from "./cs.json";
import en from "./en.json";

// Every validation code has a message in every bundled locale, and no
// message embeds a literal limit figure — a bound changes in one place
// (design `add-field-validation`, task 4.4).

const LOCALES: Record<string, Record<string, string>> = {
  cs: (cs as { validation: Record<string, string> }).validation,
  en: (en as { validation: Record<string, string> }).validation,
};

describe("validation locale parity", () => {
  for (const code of VALIDATION_CODES) {
    it(`has a message for "${code}" in every bundled locale`, () => {
      for (const [locale, messages] of Object.entries(LOCALES)) {
        expect(messages[code], `${locale} is missing validation.${code}`).toBeTruthy();
      }
    });
  }

  it("has an equal set of keys across every bundled locale", () => {
    const [first, ...rest] = Object.values(LOCALES).map((messages) => Object.keys(messages).sort());
    for (const keys of rest) {
      expect(keys).toEqual(first);
    }
  });

  it("interpolates limits as parameters rather than writing them into the text", () => {
    // a bare digit outside a {{placeholder}} would be a hardcoded limit;
    // strip every {{...}} placeholder first, then look for a stray digit
    for (const [locale, messages] of Object.entries(LOCALES)) {
      for (const [key, text] of Object.entries(messages)) {
        const withoutPlaceholders = text.replace(/\{\{.*?\}\}/g, "");
        expect(withoutPlaceholders, `${locale}.validation.${key} embeds a literal figure`).not.toMatch(/\d/);
      }
    }
  });
});

// Every operation kind names itself twice: `operation.kind.X` in a sentence
// about it, `operation.label.X` on the progress indicator. Adding a kind and
// only one of the two ships the raw key to the console — which is how
// `operation.label.statement` reached the running indicator.

const OPERATION_BUNDLES: Record<string, { kind: Record<string, string>; label: Record<string, string> }> = {
  cs: (cs as { operation: { kind: Record<string, string>; label: Record<string, string> } }).operation,
  en: (en as { operation: { kind: Record<string, string>; label: Record<string, string> } }).operation,
};

describe("operation locale parity", () => {
  for (const kind of OPERATION_KINDS) {
    it(`names "${kind}" as both a kind and a label in every bundled locale`, () => {
      for (const [locale, operation] of Object.entries(OPERATION_BUNDLES)) {
        expect(operation.kind[kind], `${locale} is missing operation.kind.${kind}`).toBeTruthy();
        expect(operation.label[kind], `${locale} is missing operation.label.${kind}`).toBeTruthy();
      }
    });
  }
});
