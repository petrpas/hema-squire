import { IconX } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Discount,
  type DiscountCondition,
  type DiscountEffect,
  type TournamentDetail,
  api,
} from "../api";
import FieldError, { invalidProps } from "../FieldError";
import { showsEur } from "../money";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkMoney, checkNumeric, checkPercent, checkString, type FieldError as FieldErrorValue } from "../validation";
import { _int, recalculateMissing, type SaverRegistry, useSectionSaver } from "./shared";

function emptyDiscount(): Discount {
  return {
    name: "",
    condition: { kind: "discipline_count", count: 2 },
    effect: { kind: "fixed", value: 0 },
    scope: ["discipline"],
  };
}

export function DiscountsSection({
  detail,
  slug,
  pricingWarning,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  pricingWarning: boolean;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Discount[]>(detail.discounts);
  const [dirty, setDirty] = useState(false);
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  function discountChecks(discount: Discount, index: number): Record<string, () => FieldErrorValue | null> {
    const scoped = (field: string) => `${field}-${index}`;
    return {
      name: () => checkString(scoped("name"), "DiscountIn.name", discount.name, { required: true }),
      count: () =>
        discount.condition.kind === "discipline_count"
          ? checkNumeric(scoped("count"), "DiscountCondition.count", String(discount.condition.count ?? ""), {
              required: true,
            })
          : null,
      value:
        discount.effect.kind === "percent"
          ? () => checkPercent(scoped("value"), String(discount.effect.value))
          : () => checkMoney(scoped("value"), String(discount.effect.value), detail.local_currency),
      value_eur: () =>
        discount.effect.kind === "fixed"
          ? checkMoney(
              scoped("value_eur"),
              discount.effect.value_eur === null || discount.effect.value_eur === undefined
                ? ""
                : String(discount.effect.value_eur),
              "EUR",
            )
          : null,
    };
  }

  useEffect(() => {
    setDrafts(detail.discounts);
    setDirty(false);
  }, [detail]);

  function update(index: number, patch: Partial<Discount>) {
    const next = [...drafts];
    next[index] = { ...next[index], ...patch };
    setDrafts(next);
    setDirty(true);
  }

  function updateCondition(index: number, patch: Partial<DiscountCondition>) {
    update(index, { condition: { ...drafts[index].condition, ...patch } });
  }

  function updateEffect(index: number, patch: Partial<DiscountEffect>) {
    update(index, { effect: { ...drafts[index].effect, ...patch } });
  }

  function recalculateAll() {
    setDrafts((prev) =>
      prev.map((discount) => {
        if (discount.effect.kind !== "fixed") return discount;
        const [value, valueEur] = recalculateMissing(
          String(discount.effect.value),
          discount.effect.value_eur === null || discount.effect.value_eur === undefined
            ? ""
            : String(discount.effect.value_eur),
          rate,
        );
        return {
          ...discount,
          effect: { ...discount.effect, value: Number(value), value_eur: valueEur === "" ? null : Number(valueEur) },
        };
      }),
    );
    setDirty(true);
  }

  useSectionSaver(registry, "payments", "discounts", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: true,
    validate: () =>
      validation.validateAll(
        drafts.flatMap((discount, index) => Object.values(discountChecks(discount, index))),
      ),
    focusFirstInvalid: () => {
      drafts.forEach((discount, index) => {
        for (const [field, check] of Object.entries(discountChecks(discount, index))) {
          if (check()) {
            fieldRefs.current[`${field}-${index}`]?.focus();
            return;
          }
        }
      });
    },
    flush: async () => {
      try {
        await api.updateTournament(slug, { discounts: drafts });
        setDirty(false);
        return [{ change: "discounts", section: "discounts", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        return [{ change: "discounts", section: "discounts", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.discounts.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.discounts.name")}</th>
            <th>{t("setup.discounts.condition")}</th>
            <th>{t("setup.discounts.effect")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {drafts.map((discount, index) => {
            const checks = discountChecks(discount, index);
            function fieldRef(field: string) {
              return (el: HTMLInputElement | null) => {
                fieldRefs.current[`${field}-${index}`] = el;
              };
            }
            function fieldErrorProps(field: string) {
              return invalidProps(`${field}-${index}`, validation.errors[`${field}-${index}`]);
            }
            function touch(field: string) {
              const check = checks[field];
              return () => {
                if (check) validation.touch(`${field}-${index}`, check);
              };
            }
            function clearIfValid(field: string) {
              const check = checks[field];
              return () => {
                if (check) validation.clearIfValid(`${field}-${index}`, check);
              };
            }
            return (
            <tr key={index}>
              <td>
                <input
                  ref={fieldRef("name")}
                  className="cell-input"
                  value={discount.name}
                  onChange={(event) => {
                    update(index, { name: event.target.value });
                    clearIfValid("name")();
                  }}
                  onBlur={touch("name")}
                  {...fieldErrorProps("name")}
                />
                <FieldError field={`name-${index}`} error={validation.errors[`name-${index}`]} />
              </td>
              <td>
                <div className="param-fields">
                  <select
                    value={discount.condition.kind}
                    onChange={(event) =>
                      updateCondition(index, {
                        kind: event.target.value as DiscountCondition["kind"],
                      })
                    }
                  >
                    <option value="discipline_count">
                      {t("setup.discounts.conditionCount")}
                    </option>
                    <option value="early">{t("setup.discounts.conditionEarly")}</option>
                  </select>
                  {discount.condition.kind === "discipline_count" ? (
                    <>
                      <input
                        ref={fieldRef("count")}
                        className="cell-input"
                        type="text"
                        inputMode="numeric"
                        value={discount.condition.count ?? ""}
                        onChange={(event) => {
                          updateCondition(index, { count: _int(event.target.value) ?? undefined });
                          clearIfValid("count")();
                        }}
                        onBlur={touch("count")}
                        {...fieldErrorProps("count")}
                      />
                      <FieldError field={`count-${index}`} error={validation.errors[`count-${index}`]} />
                    </>
                  ) : (
                    <input
                      className="cell-input"
                      type="date"
                      value={discount.condition.until ?? ""}
                      onChange={(event) =>
                        updateCondition(index, { until: event.target.value })
                      }
                    />
                  )}
                </div>
              </td>
              <td>
                <div className="param-fields">
                  <select
                    value={discount.effect.kind}
                    onChange={(event) => {
                      const kind = event.target.value as DiscountEffect["kind"];
                      // a percent effect is currency-neutral and carries no
                      // second value (design Decision 1)
                      updateEffect(index, { kind, value_eur: kind === "fixed" ? discount.effect.value_eur : null });
                    }}
                  >
                    <option value="fixed">
                      {t("setup.discounts.fixed", { currency: detail.local_currency })}
                    </option>
                    <option value="percent">{t("setup.discounts.percent")}</option>
                  </select>
                  <input
                    ref={fieldRef("value")}
                    className="cell-input"
                    type="text"
                    inputMode="numeric"
                    value={discount.effect.value}
                    onChange={(event) => {
                      updateEffect(index, { value: _int(event.target.value) ?? 0 });
                      clearIfValid("value")();
                    }}
                    onBlur={touch("value")}
                    {...fieldErrorProps("value")}
                  />
                  <FieldError field={`value-${index}`} error={validation.errors[`value-${index}`]} />
                  {eur && discount.effect.kind === "fixed" && (
                    <>
                      <input
                        ref={fieldRef("value_eur")}
                        className="cell-input"
                        type="text"
                        inputMode="numeric"
                        placeholder={t("setup.discounts.fixedEur")}
                        value={discount.effect.value_eur ?? ""}
                        onChange={(event) => {
                          updateEffect(index, {
                            value_eur: event.target.value === "" ? null : (_int(event.target.value) ?? null),
                          });
                          clearIfValid("value_eur")();
                        }}
                        onBlur={touch("value_eur")}
                        {...fieldErrorProps("value_eur")}
                      />
                      <FieldError field={`value_eur-${index}`} error={validation.errors[`value_eur-${index}`]} />
                    </>
                  )}
                </div>
              </td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  onClick={() => {
                    setDrafts(drafts.filter((_, i) => i !== index));
                    setDirty(true);
                  }}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
      <button
        className="link-button"
        onClick={() => {
          setDrafts([...drafts, emptyDiscount()]);
          setDirty(true);
        }}
      >
        + {t("setup.discounts.add")}
      </button>
      {eur && (
        <button
          className="link-button"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={recalculateAll}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
    </section>
  );
}
