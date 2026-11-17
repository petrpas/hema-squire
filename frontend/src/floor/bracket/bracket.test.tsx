// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { type BracketBout, bracketApi } from "../floorApi";
import { BracketBoutRow } from "./BracketBoutRow";

// An elimination bout (spec floor-bracket): a winner is required, and a
// walkover carries its note.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const bout: BracketBout = {
  id: 7,
  round: 0,
  position: 2,
  a: "a",
  b: "b",
  score_a: null,
  score_b: null,
  outcome_a: null,
  outcome_b: null,
  note: null,
  piste_id: 1,
  version: 0,
};

let host: HTMLElement | null = null;
let root: Root | null = null;

function mount() {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root?.render(
      <ul>
        <BracketBoutRow
          slug="cup"
          discipline={3}
          bout={bout}
          name={(k) => ({ a: "Adéla", b: "Boris" })[k] ?? k}
          label="R1"
          onChanged={() => {}}
        />
      </ul>,
    ),
  );
}

function set(element: HTMLInputElement | HTMLSelectElement | null | undefined, value: string) {
  if (!element) return;
  const proto =
    element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(proto, "value")?.set?.call(element, value);
    element.dispatchEvent(
      new Event(element instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }),
    );
  });
}

async function settle() {
  for (let i = 0; i < 4; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

function save() {
  const button = [...(host?.querySelectorAll("button") ?? [])].find(
    (b) => b.textContent === t("floor.ring.record"),
  );
  act(() => button?.click());
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("an elimination bout", () => {
  it("refuses a draw before sending it", async () => {
    const record = vi.spyOn(bracketApi, "record").mockResolvedValue(undefined);
    mount();
    const inputs = host?.querySelectorAll<HTMLInputElement>('input[type="number"]');
    set(inputs?.[0], "10");
    set(inputs?.[1], "10");

    save();
    await settle();

    expect(record).not.toHaveBeenCalled();
    expect(host?.textContent).toContain(t("floor.bracket.refusals.winner_required"));
  });

  it("records a walkover with its note, the other side advancing", async () => {
    const record = vi.spyOn(bracketApi, "record").mockResolvedValue(undefined);
    mount();
    set(host?.querySelector("select"), "a");
    set(
      host?.querySelector<HTMLInputElement>(`input[aria-label="${t("floor.bracket.note")}"]`),
      "medical",
    );

    save();
    await settle();

    expect(record).toHaveBeenCalledWith("cup", 3, 7, {
      score_a: 0,
      score_b: 0,
      outcome_a: "no",
      outcome_b: "win",
      note: "medical",
      version: 0,
    });
  });
});
