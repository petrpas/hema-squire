// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { SetupSuggestions, TournamentDetail } from "../api";
import "../i18n";
import { EMPTY_SUGGESTIONS } from "../suggestions";
import { BankAccountSection } from "./BankAccountSection";
import { SaverRegistry } from "./shared";

// The account holder sits under the account and, where the account is chosen
// from the organizer's history, arrives with it — into an empty field only
// (spec tournament-admin, setup-field-suggestions).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const ACCOUNT = "CZ6508000000192000145399";

const suggestions: SetupSuggestions = {
  ...EMPTY_SUGGESTIONS,
  bank_accounts: [ACCOUNT],
  bank_account_holders: ["TJ Šerm Praha"],
  holder_by_account: { [ACCOUNT]: "TJ Šerm Praha" },
};

let host: HTMLElement | null = null;

afterEach(() => {
  host?.remove();
  host = null;
});

function renderSection(overrides: Partial<TournamentDetail> = {}) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const detail = {
    slug: "cup",
    bank_account: null,
    bank_account_holder: null,
    fio_token_configured: false,
    ...overrides,
  } as TournamentDetail;
  act(() =>
    root.render(
      <BankAccountSection
        detail={detail}
        slug="cup"
        registry={new SaverRegistry()}
        suggestions={suggestions}
        onSaved={vi.fn()}
      />,
    ),
  );
}

function field(id: string): HTMLInputElement {
  const input = host?.querySelector<HTMLInputElement>(`#${id}`);
  if (!input) throw new Error(`no #${id}`);
  return input;
}

function chooseFirstAccount() {
  const input = field("bank-account");
  act(() => input.focus());
  act(() => {
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
  });
  act(() => {
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  });
}

it("places the holder field directly below the account", () => {
  renderSection();
  const fields = [...(host?.querySelectorAll(".form-fields > .form-field") ?? [])];
  const accountIndex = fields.findIndex((el) => el.querySelector("#bank-account"));
  expect(fields[accountIndex + 1]?.querySelector("#bank-account-holder")).not.toBeNull();
});

it("fills an empty holder from a recalled account", () => {
  renderSection();
  chooseFirstAccount();
  expect(field("bank-account").value).toBe(ACCOUNT);
  expect(field("bank-account-holder").value).toBe("TJ Šerm Praha");
});

it("leaves a holder already typed", () => {
  renderSection({ bank_account_holder: "Jan Novák" });
  chooseFirstAccount();
  expect(field("bank-account").value).toBe(ACCOUNT);
  expect(field("bank-account-holder").value).toBe("Jan Novák");
});
