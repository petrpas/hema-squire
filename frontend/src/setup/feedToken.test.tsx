// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, api, type SetupSuggestions, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { BankAccountSection } from "./BankAccountSection";
import FeedTokenDialog from "./FeedTokenDialog";
import { SaverRegistry } from "./shared";

// The bank feed token: offered beside the account it reads, only where that
// account is a Fio one, and written by a form that never shows what is stored
// (spec tournament-admin).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

const FIO_IBAN = "CZ8620100000002900123456";
const OTHER_BANK = "CZ6508000000192000145399";

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

function click(button: HTMLButtonElement | undefined) {
  act(() => void button?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function typeInto(input: HTMLInputElement | null | undefined, value: string) {
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    input?.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

function detail(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    slug: "cup",
    bank_account: null,
    fio_token_configured: false,
    ...overrides,
  } as TournamentDetail;
}

const suggestions = { bank_accounts: [] } as unknown as SetupSuggestions;

function renderSection(overrides: Partial<TournamentDetail> = {}, onSaved = vi.fn()) {
  return mount(
    <BankAccountSection
      detail={detail(overrides)}
      slug="cup"
      registry={new SaverRegistry()}
      suggestions={suggestions}
      onSaved={onSaved}
    />,
  );
}

function accountField() {
  return host?.querySelector(".form-field input") as HTMLInputElement;
}

// ------------------------------------------------------------ the action

it("offers no token action on an empty account, and says why", () => {
  renderSection();
  expect(buttonNamed(t("setup.feedToken.set"))).toBeUndefined();
  expect(host?.textContent).toContain(t("setup.feedToken.fioOnly"));
});

it("offers it as soon as a Fio account is typed, without a save", () => {
  renderSection();
  typeInto(accountField(), FIO_IBAN);
  expect(buttonNamed(t("setup.feedToken.set"))).toBeDefined();
  expect(host?.textContent).not.toContain(t("setup.feedToken.fioOnly"));
});

it("states the reason on another bank rather than hiding the action", () => {
  renderSection();
  typeInto(accountField(), OTHER_BANK);
  expect(buttonNamed(t("setup.feedToken.set"))).toBeUndefined();
  expect(host?.textContent).toContain(t("setup.feedToken.fioOnly"));
});

it("keeps the action on the account's own label line, so nothing reflows", () => {
  renderSection();
  const row = host?.querySelector(".field-label-row");
  expect(row?.querySelector(".rail-hint")).not.toBeNull();
  typeInto(accountField(), FIO_IBAN);
  // the same row now carries the action: the control changed state in place
  expect(host?.querySelector(".field-label-row .link-button")).not.toBeNull();
});

it("says whether a token is recorded, without showing one", () => {
  renderSection({ bank_account: FIO_IBAN, fio_token_configured: true });
  expect(host?.textContent).toContain(t("setup.feedToken.state.recorded"));
  expect(buttonNamed(t("setup.feedToken.reset"))).toBeDefined();
});

// ------------------------------------------------------------ the dialog

function renderDialog(
  configured = false,
  handlers: { onDone?: () => void; onClose?: () => void } = {},
) {
  return mount(
    <FeedTokenDialog
      slug="cup"
      configured={configured}
      onDone={handlers.onDone ?? vi.fn()}
      onClose={handlers.onClose ?? vi.fn()}
    />,
  );
}

function tokenField() {
  return host?.querySelector(".modal input") as HTMLInputElement;
}

it("opens with an empty field on a tournament that already has a token", () => {
  renderDialog(true);
  expect(tokenField().value).toBe("");
  expect(host?.textContent).toContain(t("setup.feedToken.recorded"));
  expect(host?.textContent).toContain(t("setup.feedToken.advice"));
});

it("writes nothing on an empty submission, so a look-and-save keeps the feed", () => {
  const set = vi.spyOn(api, "setFioToken");
  const clear = vi.spyOn(api, "clearFioToken");
  renderDialog(true);
  expect(buttonNamed(t("setup.feedToken.save"))?.disabled).toBe(true);
  click(buttonNamed(t("setup.feedToken.save")));
  expect(set).not.toHaveBeenCalled();
  expect(clear).not.toHaveBeenCalled();
});

it("records a typed token and reports the new state", async () => {
  const set = vi.spyOn(api, "setFioToken").mockResolvedValue({ configured: true, verified: true });
  const onDone = vi.fn();
  const onClose = vi.fn();
  renderDialog(false, { onDone, onClose });

  typeInto(tokenField(), "secret-token");
  click(buttonNamed(t("setup.feedToken.save")));
  await settle();

  expect(set).toHaveBeenCalledWith("cup", "secret-token");
  expect(onDone).toHaveBeenCalledWith({ configured: true, verified: true });
  expect(onClose).toHaveBeenCalled();
});

it("removes a recorded token through its own control", async () => {
  const clear = vi
    .spyOn(api, "clearFioToken")
    .mockResolvedValue({ configured: false, verified: false });
  const onDone = vi.fn();
  renderDialog(true, { onDone });

  click(buttonNamed(t("setup.feedToken.remove")));
  await settle();

  expect(clear).toHaveBeenCalledWith("cup");
  expect(onDone).toHaveBeenCalledWith({ configured: false, verified: false });
});

it("offers no removal where nothing is recorded", () => {
  renderDialog(false);
  expect(buttonNamed(t("setup.feedToken.remove"))).toBeUndefined();
});

it("stays open on a refusal, with the reason at the field", async () => {
  vi.spyOn(api, "setFioToken").mockRejectedValue(new ApiError(422, "fio_token_rejected"));
  const onClose = vi.fn();
  renderDialog(false, { onClose });

  typeInto(tokenField(), "mistyped");
  click(buttonNamed(t("setup.feedToken.save")));
  await settle();

  expect(onClose).not.toHaveBeenCalled();
  expect(host?.textContent).toContain(t("setup.feedToken.error.fio_token_rejected"));
});

it("states that an unverified token was stored, once the dialog closes", async () => {
  vi.spyOn(api, "setFioToken").mockResolvedValue({ configured: true, verified: false });
  renderSection({ bank_account: FIO_IBAN });

  click(buttonNamed(t("setup.feedToken.set")));
  typeInto(host?.querySelector(".modal input") as HTMLInputElement, "secret-token");
  click(buttonNamed(t("setup.feedToken.save")));
  await settle();

  expect(host?.textContent).toContain(t("setup.feedToken.unchecked"));
});
