// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { useTranslation } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import cs from "./i18n/cs.json";
import EventWording from "./i18n/EventWording";
import en from "./i18n/en.json";
import i18n from "./i18n/index";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// The word follows the kind (spec `discipline-less-events`): under the wording,
// a key reads its variant where it has one and its plain form where it has not.

let host: HTMLElement | null = null;

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
});

function Line({ id }: { id: string }) {
  const { t } = useTranslation();
  return <p>{t(id)}</p>;
}

function render(isEvent: boolean, id: string) {
  const page = document.createElement("div");
  document.body.append(page);
  host = page;
  act(() => {
    createRoot(page).render(
      <EventWording isEvent={isEvent}>
        <Line id={id} />
      </EventWording>,
    );
  });
  return page.textContent;
}

describe("the wording of one record", () => {
  it("agrees in gender on an event", () => {
    expect(render(true, "setup.publish.failedAlreadyPublished")).toBe(
      "Tato akce je už zveřejněná.",
    );
  });

  it("stays a tournament otherwise", () => {
    expect(render(false, "setup.publish.failedAlreadyPublished")).toBe(
      "Tento turnaj je už zveřejněný.",
    );
  });

  it("falls back to the plain form where a key has no variant", () => {
    expect(render(true, "queue.noDisciplines")).toBe(i18n.t("queue.noDisciplines"));
  });

  it("follows a change of language", async () => {
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    expect(render(true, "setup.danger.deleteButton")).toBe("Delete event");
  });
});

function entries(tree: object, path = ""): [string, string][] {
  return Object.entries(tree).flatMap(([key, value]): [string, string][] =>
    typeof value === "string" ? [[`${path}${key}`, value]] : entries(value, `${path}${key}.`),
  );
}

describe("the variants", () => {
  for (const [locale, bundle] of [
    ["cs", cs],
    ["en", en],
  ] as const) {
    it(`never say tournament in ${locale}`, () => {
      const variants = entries(bundle).filter(([key]) => key.includes("_event"));
      expect(variants.length).toBeGreaterThan(50);
      for (const [key, text] of variants) {
        expect(text, key).not.toMatch(/turnaj|tournament/i);
      }
    });

    it(`keep their base's placeholders in ${locale}`, () => {
      const flat = new Map(entries(bundle));
      const slots = (text: string) => (text.match(/\{\{\w+\}\}/g) ?? []).sort();
      for (const [key, text] of flat) {
        const base = flat.get(key.replace("_event", ""));
        if (key.includes("_event") && base !== undefined) {
          expect(slots(text), key).toEqual(slots(base));
        }
      }
    });
  }
});
