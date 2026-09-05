// @vitest-environment jsdom
import { expect, it } from "vitest";

import cs from "../i18n/cs.json";
import en from "../i18n/en.json";
import { IDENTITY_FIELDS } from "./IdentitySection";

// Every identity field takes its label from `param.<key>` and its hint from a
// key it names. A field added without them renders its own key in capitals as
// the label — which is what `external_registration_url` did, and which neither
// the type checker nor the locale-parity test can see: parity compares the two
// catalogues against each other, not against what the components ask for.

function lookup(catalogue: unknown, dotted: string): unknown {
  return dotted
    .split(".")
    .reduce<unknown>(
      (node, part) =>
        node && typeof node === "object" ? (node as Record<string, unknown>)[part] : undefined,
      catalogue,
    );
}

it.each([
  ["en", en],
  ["cs", cs],
])("every identity field has a label in %s", (_lang, catalogue) => {
  const missing = IDENTITY_FIELDS.map((field) => `param.${field.key}`).filter(
    (key) => typeof lookup(catalogue, key) !== "string",
  );
  expect(missing).toEqual([]);
});

it.each([
  ["en", en],
  ["cs", cs],
])("every identity hint resolves in %s", (_lang, catalogue) => {
  const missing = IDENTITY_FIELDS.filter(
    (field): field is typeof field & { hint: string } => "hint" in field,
  )
    .map((field) => field.hint)
    .filter((key) => typeof lookup(catalogue, key) !== "string");
  expect(missing).toEqual([]);
});
