import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Currency, type CurrencyMode, type ExtraCategory, type TournamentMode } from "../api";
import { parseInteger } from "../numeric";
import { LEGACY_WEAPONS } from "../TournamentFace";

export const TAXONOMY_WEAPON_CODES = Object.keys(LEGACY_WEAPONS);

// design Decision D1 (split-setup-into-tabs); `publish` added last (design D6
// of add-explicit-publishing) — the end of the Setup arc, offered to every
// console team member regardless of ownership. `timeline` sits between
// `extra` and `payments` (regroup-setup-parameters Decision 2) so the bar
// reads in the order the organizer works: what the tournament is, what it
// offers, what those cost, when it happens, how it is paid for.
export type SetupTab =
  | "tournament"
  | "disciplines"
  | "extra"
  | "timeline"
  | "payments"
  | "other"
  | "publish";
export const SETUP_TABS: SetupTab[] = [
  "tournament",
  "disciplines",
  "extra",
  "timeline",
  "payments",
  "other",
  "publish",
];

/** Which tabs the tournament's mode offers, in the fixed order above — the
 *  mode removes tabs, it never reorders them (spec: setup-navigation).
 *  `EXTRA` follows the extra services feature; `OTHER` keeps its owner-only
 *  restriction; the remaining five are always offered, so an easy-mode
 *  tournament is navigated by six. */
export function offeredSetupTabs(mode: TournamentMode, isOwner: boolean): SetupTab[] {
  return SETUP_TABS.filter((tab) => {
    if (tab === "extra") return mode.feature_extras;
    if (tab === "other") return isOwner;
    return true;
  });
}

/** The tab's title. Only the payments tab's changes with the mode: what it
 *  then holds is the currency the tournament prices in and the discounts it
 *  gives, and a tab titled for payments on a tournament that takes none
 *  states something untrue (design D7). Its identifier stays `payments` —
 *  the URL, the marker attribution and `aria-controls` are built from that. */
export function setupTabTitleKey(tab: SetupTab, mode: TournamentMode): string {
  if (tab === "payments" && !mode.feature_payments) return "setup.tabs.pricing";
  return `setup.tabs.${tab}`;
}

// Keys are exactly those backend/app/setup.py emits (D1). Every key it can
// emit has an entry here, and the tab named holds a section that resolves it
// (regroup-setup-parameters Decision 1) — that is what makes an item read on
// PUBLISH traceable to somewhere it can actually be fixed.
//
// A key absent from this map marks no tab, so an unrecognized checklist item
// never breaks the bar. That fallback is for a backend ahead of a deployed
// client; it is not where a key this client is expected to resolve belongs.
export const MISSING_TAB: Record<string, SetupTab> = {
  location: "tournament",
  organizers: "tournament",
  disciplines: "disciplines",
  discipline_prices: "disciplines",
  team_bounds: "disciplines",
  extra_item_prices: "extra",
  discount_prices: "payments",
  // resolved by PaymentModeSection's deposit field
  deposit_amount: "payments",
  // resolved by LegacyFeesSection's clear action
  legacy_fixed_fees_block_eur: "payments",
  bank_account: "payments",
};

// The feature whose absence takes a missing item's editor out of Setup. The
// item is still reported — completeness reads the tournament's contents, not
// its features (design D4) — but there is nowhere to fix it until the feature
// is turned back on, so it marks `PUBLISH` alone and `PUBLISH` names the way
// back (spec: setup-navigation). Items that cannot arise in a mode at all —
// the bank account and the deposit while payments are off — are not reported
// by the backend and never reach here.
export const MISSING_FEATURE: Record<string, keyof TournamentMode> = {
  extra_item_prices: "feature_extras",
  team_bounds: "feature_teams",
};

/** The feature a missing item needs turned on before it can be edited, or
 *  undefined when its editor is already offered. */
export function concealedBy(key: string, mode: TournamentMode): keyof TournamentMode | undefined {
  const feature = MISSING_FEATURE[key];
  return feature !== undefined && !mode[feature] ? feature : undefined;
}

/** The tab a missing item marks, or undefined when no tab does: either the
 *  client does not recognize the item, or the mode conceals its editor. */
export function missingTab(key: string, mode: TournamentMode): SetupTab | undefined {
  if (concealedBy(key, mode) !== undefined) return undefined;
  return MISSING_TAB[key];
}

// Fixed flush/registration order, independent of effect-firing order (D7).
// `paymentMode` precedes `bankAccount`: how fencers pay stands first on the
// payments tab, before the account the money arrives in.
export const SECTION_ORDER = [
  "identity",
  "organizers",
  "disciplines",
  "extra",
  "timeline",
  "paymentMode",
  "bankAccount",
  "currency",
  "vsSeries",
  "discounts",
  "legacyFees",
  "exportSheet",
] as const;

export type SaveOutcome = {
  change: string;
  section: string;
  error: string | null;
};

export type SectionSaver = {
  pendingCount: number;
  touchesPrice: boolean;
  // runs every field check, shows each result, and reports how many fields
  // are invalid — 0 means the section may flush (design D5)
  validate: () => number;
  // moves focus to this section's first invalid field; a no-op when none is
  // invalid. Called only when the blocked-save statement is activated, not
  // when validate() itself runs (design: "activating that statement focuses
  // the first invalid field")
  focusFirstInvalid: () => void;
  flush: () => Promise<SaveOutcome[]>;
};

/** Holds every mounted section's saver, keyed by section id, and notifies
 * subscribers (the save bar, the dirty-count effect) on any change (D7). */
export class SaverRegistry {
  private entries = new Map<string, { tab: SetupTab; saver: SectionSaver }>();
  private version = 0;
  private listeners = new Set<() => void>();

  set(id: string, tab: SetupTab, saver: SectionSaver) {
    // The saver closure is refreshed on every call so flush()/validate() are
    // never stale, but subscribers are only notified when a value they
    // actually display changes — otherwise every keystroke in an
    // already-dirty section would re-render the whole registry's
    // subscribers forever (each re-render re-registers, which would
    // re-notify, which would re-render...).
    const prev = this.entries.get(id);
    this.entries.set(id, { tab, saver });
    if (
      !prev ||
      prev.tab !== tab ||
      prev.saver.pendingCount !== saver.pendingCount ||
      prev.saver.touchesPrice !== saver.touchesPrice
    ) {
      this.version++;
      for (const listener of this.listeners) listener();
    }
  }

  delete(id: string) {
    if (!this.entries.delete(id)) return;
    this.version++;
    for (const listener of this.listeners) listener();
  }

  forTab(tab: SetupTab): { id: string; saver: SectionSaver }[] {
    return [...this.entries.entries()]
      .filter(([, entry]) => entry.tab === tab)
      .map(([id, entry]) => ({ id, saver: entry.saver }))
      .sort(
        (a, b) =>
          SECTION_ORDER.indexOf(a.id as (typeof SECTION_ORDER)[number]) -
          SECTION_ORDER.indexOf(b.id as (typeof SECTION_ORDER)[number]),
      );
  }

  all(): { id: string; tab: SetupTab; saver: SectionSaver }[] {
    return [...this.entries.entries()].map(([id, entry]) => ({ id, ...entry }));
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  getVersion = () => this.version;
}

/** Registers (and, on unmount, unregisters) a section's saver. Sections stay
 * mounted for the life of the Setup phase (D2), so unregistration in
 * practice only happens when SetupPanel itself unmounts. */
export function useSectionSaver(registry: SaverRegistry, tab: SetupTab, id: string, saver: SectionSaver) {
  useEffect(() => {
    registry.set(id, tab, saver);
  });
  useEffect(() => () => registry.delete(id), [registry, id]);
}

export const CURRENCY_MODES: CurrencyMode[] = ["local", "local_eur", "eur"];
// the only local (non-EUR) currency today (design Decision 6); a picker
// among several local currencies is future scope
export const LOCAL_CURRENCY: Currency = "CZK";

/** Fills empty EUR/local price pairs from filled ones at `rate`, rounded
 * half-up to whole units, in either direction — never overwriting a typed
 * value (design Decision 3). The one place `eur_rate` touches money. */
export function recalculateMissing(local: string, eur: string, rate: number): [string, string] {
  if (!Number.isFinite(rate) || rate <= 0) return [local, eur];
  if (eur === "" && local !== "" && Number.isFinite(Number(local))) {
    return [local, String(Math.round(Number(local) / rate))];
  }
  if (local === "" && eur !== "" && Number.isFinite(Number(eur))) {
    return [String(Math.round(Number(eur) * rate)), eur];
  }
  return [local, eur];
}

/** Guards a save action behind the price-change confirmation when the
 * tournament already has registrations (design Decision 7): existing
 * registrations keep their quoted amount, amending fencers are repriced,
 * new registrations use the new price. */
export function usePriceChangeGuard() {
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  // `shouldWarn` is passed at call time rather than bound once from a hook
  // parameter, so it reflects the state at the moment of saving rather than
  // whatever it was at the caller's last render.
  function guard(shouldWarn: boolean, action: () => void) {
    if (shouldWarn) setPendingAction(() => action);
    else action();
  }
  function confirm() {
    const action = pendingAction;
    setPendingAction(null);
    action?.();
  }
  function cancel() {
    setPendingAction(null);
  }
  return { guard, confirming: pendingAction !== null, confirm, cancel };
}

export function PriceChangeWarning({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="rail-card dashed">
      <p>{t("setup.priceChangeWarning.title")}</p>
      <ul className="detail-list">
        <li>{t("setup.priceChangeWarning.existing")}</li>
        <li>{t("setup.priceChangeWarning.amending")}</li>
        <li>{t("setup.priceChangeWarning.new")}</li>
      </ul>
      <p className="rail-hint">{t("setup.priceChangeWarning.badPractice")}</p>
      <div className="modal-actions">
        <button type="button" className="secondary" onClick={onCancel}>
          {t("common.cancel")}
        </button>
        <button type="button" className="btn-primary" onClick={onConfirm}>
          {t("setup.priceChangeWarning.proceed")}
        </button>
      </div>
    </div>
  );
}

/** Option choices are typed as one comma-separated line; the backend trims and
 *  deduplicates, so this only has to split. */
export function splitChoices(value: string): string[] {
  return value.split(",").map((choice) => choice.trim()).filter(Boolean);
}

export const EXTRA_CATEGORIES: ExtraCategory[] = [
  "seminar",
  "afterparty",
  "other_action",
  "rental",
  "merch",
  "other_item",
];

// action categories happen at a time and place (when/where, no quantity
// limit); item categories are goods (quantity limit, no when/where) — D4
export const ACTION_EXTRA_CATEGORIES = new Set<ExtraCategory>(["seminar", "afterparty", "other_action"]);
export function isActionCategory(category: ExtraCategory): boolean {
  return ACTION_EXTRA_CATEGORIES.has(category);
}

// shared by DisciplinesSection, ExtraItemsSection, and DiscountsSection
export function _int(raw: string): number | null {
  const result = parseInteger(raw);
  return result.ok ? result.value : null;
}
