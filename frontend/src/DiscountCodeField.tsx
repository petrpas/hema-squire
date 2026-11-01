import { useTranslation } from "react-i18next";

import type { DiscountBreakdown } from "./api";
import { formatMoneyWithEur } from "./money";

/** What a code took off, as the fencer reads it. */
export function DiscountCodeLine({
  applied,
  detail,
}: {
  applied: DiscountBreakdown;
  detail: Parameters<typeof formatMoneyWithEur>[2];
}) {
  const { t } = useTranslation();
  return (
    <p className="rail-hint">
      {t("discountCode.applied", {
        name: applied.name,
        amount: t("discounts.amountValue", {
          amount: formatMoneyWithEur(applied.deducted ?? 0, applied.deducted_eur, detail),
        }),
      })}
    </p>
  );
}

/** Where a fencer types a code they were given. The server decides what it is
 *  worth: this only hands the text over and states the answer, and a refusal
 *  says the same whether the code never existed or has run out (spec
 *  discount-codes). */
export function DiscountCodeField({
  value,
  onChange,
  onApply,
  disabled,
  refused,
}: {
  value: string;
  onChange: (value: string) => void;
  onApply: () => void;
  disabled: boolean;
  refused: boolean;
}) {
  const { t } = useTranslation();
  return (
    <>
      <h3 className="register-section">{t("discountCode.title")}</h3>
      <div className="form-fields">
        <label className="form-field">
          <span>{t("discountCode.label")}</span>
          <input
            value={value}
            autoComplete="off"
            onChange={(event) => onChange(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="link-button"
          disabled={disabled || value.trim() === ""}
          onClick={onApply}
        >
          {t("discountCode.apply")}
        </button>
      </div>
      {refused && <p className="login-error">{t("discountCode.refused")}</p>}
    </>
  );
}
