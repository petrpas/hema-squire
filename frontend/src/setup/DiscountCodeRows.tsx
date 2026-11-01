import { IconX } from "@tabler/icons-react";
import { Fragment, type MutableRefObject } from "react";
import { useTranslation } from "react-i18next";

import type { Currency, DiscountEffect } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import { slugify } from "../slugify";
import type { useFieldValidation } from "../useFieldValidation";
import type { FieldError as FieldErrorValue } from "../validation";
import { _int } from "./shared";

const CATEGORIES = [
  "discipline",
  "seminar",
  "rental",
  "afterparty",
  "merch",
  "other_action",
  "other_item",
] as const;

export interface Draft {
  /** React's identity for the row: a new one has no id yet. */
  rowId: string;
  id: number | null;
  name: string;
  code: string;
  /** The code stops following the name once the organizer has typed in it. */
  codeEdited: boolean;
  maxUses: string;
  effect: DiscountEffect;
  scope: string[];
  uses: number;
  /** A registration carries it, so what it means can no longer change. */
  locked: boolean;
  changed: boolean;
}

/** One code's table row, and below it the categories where a percentage names
 *  some. */
export function DiscountCodeRows({
  draft,
  index,
  eur,
  currency,
  checks,
  validation,
  fieldRefs,
  update,
  onRemove,
}: {
  draft: Draft;
  index: number;
  eur: boolean;
  currency: Currency;
  checks: Record<string, () => FieldErrorValue | null>;
  validation: ReturnType<typeof useFieldValidation>;
  fieldRefs: MutableRefObject<Record<string, HTMLInputElement | null>>;
  update: (patch: Partial<Draft>) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const id = (name: string) => `code-${name}-${index}`;
  const field = (name: string) => ({
    ref: (el: HTMLInputElement | null) => {
      fieldRefs.current[id(name)] = el;
    },
    onBlur: () => {
      const run = checks[name];
      if (run) validation.touch(id(name), run);
    },
    ...invalidProps(id(name), validation.errors[id(name)]),
  });
  const error = (name: string) => (
    <FieldError field={id(name)} error={validation.errors[id(name)]} />
  );
  const lockedHint = draft.locked ? t("setup.discountCodes.locked") : undefined;

  return (
    <Fragment>
      <tr>
        <td>
          <input
            className="cell-input"
            value={draft.name}
            {...field("name")}
            onChange={(event) => {
              const name = event.target.value;
              update(draft.codeEdited ? { name } : { name, code: slugify(name) });
            }}
          />
          {error("name")}
        </td>
        <td>
          <input
            className="cell-input"
            value={draft.code}
            disabled={draft.locked}
            title={lockedHint}
            {...field("code")}
            onChange={(event) => update({ code: event.target.value, codeEdited: true })}
          />
          {error("code")}
        </td>
        <td className="col-num">
          <input
            className="cell-input"
            type="text"
            inputMode="numeric"
            value={draft.maxUses}
            placeholder={t("setup.discountCodes.unlimited")}
            {...field("max_uses")}
            onChange={(event) => update({ maxUses: event.target.value })}
          />
          {error("max_uses")}
        </td>
        <td className="col-num">
          <select
            value={draft.effect.kind}
            disabled={draft.locked}
            title={lockedHint}
            onChange={(event) =>
              update({
                effect: {
                  kind: event.target.value as DiscountEffect["kind"],
                  value: draft.effect.value,
                },
              })
            }
          >
            <option value="percent">{t("setup.discounts.percent")}</option>
            <option value="fixed">{t("setup.discounts.fixed", { currency })}</option>
          </select>
          {draft.effect.kind === "percent" && (
            <select
              aria-label={t("setup.discountCodes.scope")}
              value={draft.scope.length === 0 ? "whole" : "categories"}
              disabled={draft.locked}
              title={lockedHint}
              onChange={(event) =>
                update({ scope: event.target.value === "whole" ? [] : ["discipline"] })
              }
            >
              <option value="whole">{t("setup.discountCodes.scopeWhole")}</option>
              <option value="categories">{t("setup.discountCodes.scopeCategories")}</option>
            </select>
          )}
        </td>
        <td className="col-num">
          <input
            className="cell-input"
            type="text"
            inputMode="numeric"
            value={draft.effect.value}
            disabled={draft.locked}
            title={lockedHint}
            {...field("value")}
            onChange={(event) =>
              update({ effect: { ...draft.effect, value: _int(event.target.value) ?? 0 } })
            }
          />
          {error("value")}
        </td>
        {eur && (
          <td className="col-num">
            {draft.effect.kind === "fixed" && (
              <input
                className="cell-input"
                type="text"
                inputMode="numeric"
                value={draft.effect.value_eur ?? ""}
                disabled={draft.locked}
                title={lockedHint}
                onChange={(event) =>
                  update({
                    effect: { ...draft.effect, value_eur: _int(event.target.value) ?? null },
                  })
                }
              />
            )}
          </td>
        )}
        <td className="col-num">{draft.uses}</td>
        <td className="col-actions">
          {!draft.locked && (
            <button
              type="button"
              className="row-action"
              title={t("actions.delete")}
              onClick={onRemove}
            >
              <IconX size={16} stroke={1.5} />
            </button>
          )}
        </td>
      </tr>
      {draft.effect.kind === "percent" && draft.scope.length > 0 && (
        <tr>
          <td colSpan={eur ? 8 : 7}>
            <fieldset className="code-scope" disabled={draft.locked} title={lockedHint}>
              <legend className="visually-hidden">{t("setup.discountCodes.scope")}</legend>
              {CATEGORIES.map((category) => (
                <label key={category}>
                  <input
                    type="checkbox"
                    checked={draft.scope.includes(category)}
                    onChange={(event) =>
                      update({
                        scope: event.target.checked
                          ? [...draft.scope, category]
                          : draft.scope.filter((held) => held !== category),
                      })
                    }
                  />
                  {category === "discipline"
                    ? t("setup.discountCodes.disciplines")
                    : t(`setup.extras.categories.${category}`)}
                </label>
              ))}
            </fieldset>
          </td>
        </tr>
      )}
    </Fragment>
  );
}
