import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type DiscountCode, type DiscountCodePayload, type TournamentDetail } from "../api";
import { showsEur } from "../money";
import { useFieldValidation } from "../useFieldValidation";
import {
  apiErrors,
  checkMoney,
  checkNumeric,
  checkPercent,
  checkString,
  type FieldError as FieldErrorValue,
} from "../validation";
import { DiscountCodeRows, type Draft } from "./DiscountCodeRows";
import { type SaverRegistry, saveFailureMessage, useSectionSaver } from "./shared";

let nextRowId = 0;

function toDraft(code: DiscountCode): Draft {
  return {
    rowId: `code-${nextRowId++}`,
    id: code.id,
    name: code.name,
    code: code.code,
    codeEdited: true,
    maxUses: code.max_uses === null ? "" : String(code.max_uses),
    effect: code.effect,
    scope: code.scope,
    uses: code.uses,
    locked: code.locked,
    changed: false,
  };
}

function emptyDraft(): Draft {
  return {
    rowId: `code-${nextRowId++}`,
    id: null,
    name: "",
    code: "",
    codeEdited: false,
    maxUses: "",
    effect: { kind: "percent", value: 10 },
    scope: [],
    uses: 0,
    locked: false,
    changed: true,
  };
}

function payload(draft: Draft): DiscountCodePayload {
  return {
    name: draft.name,
    code: draft.code,
    max_uses: draft.maxUses.trim() === "" ? null : Number(draft.maxUses),
    effect: draft.effect,
    scope: draft.effect.kind === "fixed" ? [] : draft.scope,
  };
}

/** Private discounts an organizer hands out. Saved row by row through their own
 *  endpoints, since no code travels on the tournament a visitor reads (design
 *  add-discount-codes D1). */
export function DiscountCodesSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [removed, setRemoved] = useState<number[]>([]);
  const eur = showsEur(detail);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const load = useCallback(async () => {
    const codes = await api.listDiscountCodes(slug);
    setDrafts(codes.map(toDraft));
    setRemoved([]);
  }, [slug]);

  useEffect(() => {
    load().catch(() => setDrafts([]));
  }, [load]);

  function update(index: number, patch: Partial<Draft>) {
    setDrafts((prev) =>
      prev.map((draft, i) => (i === index ? { ...draft, ...patch, changed: true } : draft)),
    );
  }

  function checks(draft: Draft, index: number): Record<string, () => FieldErrorValue | null> {
    const scoped = (field: string) => `code-${field}-${index}`;
    const fixed = draft.effect.kind === "fixed";
    return {
      name: () =>
        checkString(scoped("name"), "DiscountCodeIn.name", draft.name, { required: true }),
      code: () =>
        checkString(scoped("code"), "DiscountCodeIn.code", draft.code, { required: true }),
      max_uses: () => checkNumeric(scoped("max_uses"), "DiscountCodeIn.max_uses", draft.maxUses),
      value: () =>
        fixed
          ? checkMoney(scoped("value"), String(draft.effect.value), detail.local_currency)
          : checkPercent(scoped("value"), String(draft.effect.value)),
    };
  }

  const pending = drafts.filter((draft) => draft.changed).length + removed.length;

  useSectionSaver(registry, "payments", "discount-codes", {
    pendingCount: pending,
    touchesPrice: false,
    validate: () =>
      validation.validateAll(drafts.flatMap((draft, index) => Object.values(checks(draft, index)))),
    focusFirstInvalid: () => {
      drafts.forEach((draft, index) => {
        for (const [field, check] of Object.entries(checks(draft, index))) {
          if (check()) {
            fieldRefs.current[`code-${field}-${index}`]?.focus();
            return;
          }
        }
      });
    },
    flush: async () => {
      try {
        for (const id of removed) await api.deleteDiscountCode(slug, id);
        for (const draft of drafts) {
          if (!draft.changed) continue;
          if (draft.id === null) await api.createDiscountCode(slug, payload(draft));
          else await api.updateDiscountCode(slug, draft.id, payload(draft));
        }
        await load();
        return [{ change: "discount-codes", section: "discount-codes", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        const message = saveFailureMessage(err, fieldErrors, detail, t);
        return [{ change: "discount-codes", section: "discount-codes", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.discountCodes.title")}</h2>
      <p className="rail-hint">{t("setup.discountCodes.hint")}</p>
      {drafts.length > 0 && (
        <div className="code-table">
          <table className="sheet-table">
            <thead>
              <tr>
                <th>{t("setup.discountCodes.name")}</th>
                <th>{t("setup.discountCodes.code")}</th>
                <th className="col-num">{t("setup.discountCodes.limit")}</th>
                <th className="col-num">{t("setup.discountCodes.effect")}</th>
                <th className="col-num">{t("setup.discountCodes.value")}</th>
                {eur && <th className="col-num">{t("setup.discountCodes.valueEur")}</th>}
                <th className="col-num">{t("setup.discountCodes.uses")}</th>
                <th className="col-actions" />
              </tr>
            </thead>
            <tbody>
              {drafts.map((draft, index) => (
                <DiscountCodeRows
                  key={draft.rowId}
                  draft={draft}
                  index={index}
                  eur={eur}
                  currency={detail.local_currency}
                  checks={checks(draft, index)}
                  validation={validation}
                  fieldRefs={fieldRefs}
                  update={(patch) => update(index, patch)}
                  onRemove={() => {
                    if (draft.id !== null) {
                      const id = draft.id;
                      setRemoved((prev) => [...prev, id]);
                    }
                    setDrafts(drafts.filter((_, i) => i !== index));
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button
        type="button"
        className="link-button"
        onClick={() => setDrafts([...drafts, emptyDraft()])}
      >
        + {t("setup.discountCodes.add")}
      </button>
    </section>
  );
}
