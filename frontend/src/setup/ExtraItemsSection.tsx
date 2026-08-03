import { IconX } from "@tabler/icons-react";
import { Fragment, type ChangeEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Currency,
  type ExtraCategory,
  type ExtraItem,
  type ExtraItemInput,
  type TournamentDetail,
  api,
} from "../api";
import { EXTRA_ITEM_MAX_QTY_CEILING } from "../constraints";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { showsEur } from "../money";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkMoney, checkNumeric, checkString, type FieldError as FieldErrorValue } from "../validation";
import {
  _int,
  EXTRA_CATEGORIES,
  isActionCategory,
  recalculateMissing,
  type SaverRegistry,
  type SaveOutcome,
  splitChoices,
  useSectionSaver,
} from "./shared";

type ExtraRow = Omit<ExtraItem, "id"> & {
  rowId: string;
  id: number | null;
  isNew: boolean;
  error: string | null;
  // The raw text of the choices input, kept separate from the parsed
  // `option_choices` array so typing a comma isn't immediately stripped by
  // re-deriving the field's displayed value from the trimmed/filtered array.
  optionChoicesText: string;
};

function extraItemToRow(item: ExtraItem): ExtraRow {
  return {
    ...item,
    rowId: String(item.id),
    isNew: false,
    error: null,
    optionChoicesText: item.option_choices.join(", "),
  };
}

function blankExtraRow(rowId: string): ExtraRow {
  return {
    rowId,
    id: null,
    isNew: true,
    error: null,
    name: "",
    category: "rental",
    price: 0,
    price_eur: null,
    max_qty: 1,
    schedule_when: null,
    schedule_where: null,
    remark: null,
    option_label: null,
    option_choices: [],
    optionChoicesText: "",
  };
}

function extraRowDirty(row: ExtraRow, detail: TournamentDetail): boolean {
  const item = detail.extra_items.find((i) => i.id === row.id);
  if (!item) return false;
  return (
    row.name !== item.name ||
    row.category !== item.category ||
    row.price !== item.price ||
    row.price_eur !== item.price_eur ||
    row.max_qty !== item.max_qty ||
    (row.schedule_when ?? "") !== (item.schedule_when ?? "") ||
    (row.schedule_where ?? "") !== (item.schedule_where ?? "") ||
    (row.remark ?? "") !== (item.remark ?? "") ||
    (row.option_label ?? "") !== (item.option_label ?? "") ||
    row.option_choices.join(",") !== item.option_choices.join(",")
  );
}

function extraRowTouchesPrice(row: ExtraRow, detail: TournamentDetail): boolean {
  if (row.isNew) return true;
  const item = detail.extra_items.find((i) => i.id === row.id);
  if (!item) return false;
  return row.price !== item.price || row.price_eur !== item.price_eur;
}

/** Per-field checks for one extra-item row, scoped by row id the same way
 * `disciplineRowChecks` is (design D3, task 6.1/6.4). */
function extraRowChecks(row: ExtraRow, currency: Currency): Record<string, () => FieldErrorValue | null> {
  const scoped = (field: string) => `${field}-${row.rowId}`;
  return {
    name: () => checkString(scoped("name"), "ExtraItemIn.name", row.name, { required: true }),
    price: () => checkMoney(scoped("price"), String(row.price), currency),
    price_eur: () => checkMoney(scoped("price_eur"), row.price_eur === null ? "" : String(row.price_eur), "EUR"),
    max_qty: () => {
      if (isActionCategory(row.category)) return null;
      const key = scoped("max_qty");
      const basic = checkNumeric(key, "ExtraItemIn.max_qty", String(row.max_qty), { required: true });
      if (basic) return basic;
      const ceiling = EXTRA_ITEM_MAX_QTY_CEILING[row.category];
      if (ceiling !== undefined && row.max_qty > ceiling) {
        return { field: key, code: "out_of_range", params: { min: 1, max: ceiling } };
      }
      return null;
    },
    schedule_when: () =>
      isActionCategory(row.category)
        ? checkString(scoped("schedule_when"), "ExtraItemIn.schedule_when", row.schedule_when ?? "")
        : null,
    schedule_where: () =>
      isActionCategory(row.category)
        ? checkString(scoped("schedule_where"), "ExtraItemIn.schedule_where", row.schedule_where ?? "")
        : null,
    remark: () => checkString(scoped("remark"), "ExtraItemIn.remark", row.remark ?? "", { multiline: true }),
    option_label: () =>
      checkString(scoped("option_label"), "ExtraItemIn.option_label", row.option_label ?? ""),
  };
}

function extraRowInput(row: ExtraRow): ExtraItemInput {
  return {
    name: row.name,
    category: row.category,
    price: row.price,
    price_eur: row.price_eur,
    max_qty: row.max_qty,
    schedule_when: row.schedule_when || null,
    schedule_where: row.schedule_where || null,
    remark: row.remark || null,
    option_label: row.option_label || null,
    // an option-less item must not carry leftover choices
    option_choices: row.option_label ? row.option_choices : [],
  };
}

export function ExtraItemsSection({
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
  const [rows, setRows] = useState<ExtraRow[]>(() => detail.extra_items.map(extraItemToRow));
  const [removed, setRemoved] = useState<Set<number>>(new Set());
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);
  const nextTempId = useRef(0);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const rowsRef = useRef(rows);
  rowsRef.current = rows;
  const removedRef = useRef(removed);
  removedRef.current = removed;

  // Reseed from the freshly saved detail only while the section holds no
  // pending changes (D8), matching the discipline table's guard.
  useEffect(() => {
    const clean =
      removedRef.current.size === 0 &&
      rowsRef.current.every((row) => !row.isNew && !extraRowDirty(row, detail));
    if (clean) {
      setRows(detail.extra_items.map(extraItemToRow));
      setRemoved(new Set());
    }
  }, [detail]);

  function patchRow(rowId: string, patch: Partial<ExtraRow>) {
    setRows((prev) => prev.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)));
  }

  function removeRow(row: ExtraRow) {
    setRows((prev) => prev.filter((r) => r.rowId !== row.rowId));
    if (!row.isNew && row.id !== null) setRemoved((prev) => new Set(prev).add(row.id!));
  }

  function addRow() {
    setRows((prev) => [...prev, blankExtraRow(`new-${nextTempId.current++}`)]);
  }

  function recalculateAll() {
    setRows((prev) =>
      prev.map((row) => {
        const [price, price_eur] = recalculateMissing(
          String(row.price),
          row.price_eur === null ? "" : String(row.price_eur),
          rate,
        );
        return { ...row, price: Number(price), price_eur: price_eur === "" ? null : Number(price_eur) };
      }),
    );
  }

  const pendingExtraCount =
    removed.size + rows.filter((row) => row.isNew || extraRowDirty(row, detail)).length;

  function allExtraChecks(): Array<() => FieldErrorValue | null> {
    return rows.flatMap((row) => Object.values(extraRowChecks(row, detail.local_currency)));
  }

  useSectionSaver(registry, "extra", "extra", {
    pendingCount: pendingExtraCount,
    touchesPrice: rows.some((row) => extraRowTouchesPrice(row, detail)),
    validate: () => validation.validateAll(allExtraChecks()),
    focusFirstInvalid: () => {
      for (const row of rows) {
        for (const [field, check] of Object.entries(extraRowChecks(row, detail.local_currency))) {
          if (check()) {
            fieldRefs.current[`${field}-${row.rowId}`]?.focus();
            return;
          }
        }
      }
    },
    flush: async () => {
      const outcomes: SaveOutcome[] = [];
      const stillRemoved = new Set<number>();
      for (const id of removed) {
        try {
          await api.deleteExtraItem(slug, id);
          outcomes.push({ change: String(id), section: "extra", error: null });
        } catch (err) {
          stillRemoved.add(id);
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          outcomes.push({ change: String(id), section: "extra", error: message });
        }
      }

      const results = new Map<string, string | null>();
      for (const row of rowsRef.current.filter((row) => !row.isNew && extraRowDirty(row, detail))) {
        try {
          await api.updateExtraItem(slug, row.id!, extraRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.name, section: "extra", error: null });
        } catch (err) {
          const fieldErrors = apiErrors(err).map((e) => ({ ...e, field: `${e.field}-${row.rowId}` }));
          validation.applyApiErrors(fieldErrors);
          const message =
            fieldErrors.length > 0
              ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
              : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
          results.set(row.rowId, message);
          outcomes.push({ change: row.name, section: "extra", error: message });
        }
      }
      for (const row of rowsRef.current.filter((row) => row.isNew)) {
        try {
          await api.addExtraItem(slug, extraRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.name, section: "extra", error: null });
        } catch (err) {
          const fieldErrors = apiErrors(err).map((e) => ({ ...e, field: `${e.field}-${row.rowId}` }));
          validation.applyApiErrors(fieldErrors);
          const message =
            fieldErrors.length > 0
              ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
              : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
          results.set(row.rowId, message);
          outcomes.push({ change: row.name, section: "extra", error: message });
        }
      }

      setRemoved(stillRemoved);
      setRows((prev) =>
        prev.map((row) => {
          const result = results.get(row.rowId);
          if (result === undefined) return row;
          return result === null ? { ...row, isNew: false, error: null } : { ...row, error: result };
        }),
      );
      return outcomes;
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.extras.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.extras.name")}</th>
            <th>{t("setup.extras.category")}</th>
            <th>{t("setup.extras.price", { currency: detail.local_currency })}</th>
            {eur && <th>{t("setup.extras.priceEur")}</th>}
            <th>{t("setup.extras.maxQty")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const checks = extraRowChecks(row, detail.local_currency);
            function fieldProps(field: string, value: string, onValue: (value: string) => Partial<ExtraRow>) {
              const check = checks[field];
              const scopedKey = `${field}-${row.rowId}`;
              return {
                ref: (el: HTMLInputElement | null) => {
                  fieldRefs.current[scopedKey] = el;
                },
                value,
                onChange: (event: ChangeEvent<HTMLInputElement>) => {
                  patchRow(row.rowId, onValue(event.target.value));
                  if (check) validation.clearIfValid(scopedKey, check);
                },
                onBlur: () => {
                  if (check) validation.touch(scopedKey, check);
                },
                ...invalidProps(scopedKey, validation.errors[scopedKey]),
              };
            }
            return (
            <Fragment key={row.rowId}>
              <tr>
                <td>
                  <input
                    className="cell-input"
                    {...fieldProps("name", row.name, (value) => ({ name: value }))}
                  />
                  <FieldError field={`name-${row.rowId}`} error={validation.errors[`name-${row.rowId}`]} />
                </td>
                <td>
                  <select
                    value={row.category}
                    onChange={(event) => {
                      const category = event.target.value as ExtraCategory;
                      const action = isActionCategory(category);
                      patchRow(row.rowId, {
                        category,
                        max_qty: action ? 1 : row.max_qty,
                        schedule_when: action ? row.schedule_when : null,
                        schedule_where: action ? row.schedule_where : null,
                      });
                    }}
                  >
                    {EXTRA_CATEGORIES.map((category) => (
                      <option key={category} value={category}>
                        {t(`setup.extras.categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="text"
                    inputMode="numeric"
                    {...fieldProps("price", String(row.price), (value) => ({
                      price: _int(value) ?? 0,
                    }))}
                  />
                  <FieldError field={`price-${row.rowId}`} error={validation.errors[`price-${row.rowId}`]} />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="text"
                      inputMode="numeric"
                      {...fieldProps("price_eur", row.price_eur === null ? "" : String(row.price_eur), (value) => ({
                        price_eur: value === "" ? null : _int(value),
                      }))}
                    />
                    <FieldError field={`price_eur-${row.rowId}`} error={validation.errors[`price_eur-${row.rowId}`]} />
                  </td>
                )}
                <td>
                  {!isActionCategory(row.category) && (
                    <>
                      <input
                        className="cell-input"
                        type="text"
                        inputMode="numeric"
                        {...fieldProps("max_qty", String(row.max_qty), (value) => ({
                          max_qty: _int(value) ?? 1,
                        }))}
                      />
                      <FieldError field={`max_qty-${row.rowId}`} error={validation.errors[`max_qty-${row.rowId}`]} />
                    </>
                  )}
                </td>
                <td className="col-actions">
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    onClick={() => removeRow(row)}
                  >
                    <IconX size={16} stroke={1.5} />
                  </button>
                </td>
              </tr>
              <tr className="detail-subrow">
                <td colSpan={eur ? 6 : 5}>
                  <div className="param-fields">
                    {isActionCategory(row.category) && (
                      <>
                        <label className="param-field">
                          <span>{t("setup.extras.when")}</span>
                          <input {...fieldProps("schedule_when", row.schedule_when ?? "", (value) => ({ schedule_when: value }))} />
                          <FieldError field={`schedule_when-${row.rowId}`} error={validation.errors[`schedule_when-${row.rowId}`]} />
                        </label>
                        <label className="param-field">
                          <span>{t("setup.extras.where")}</span>
                          <input {...fieldProps("schedule_where", row.schedule_where ?? "", (value) => ({ schedule_where: value }))} />
                          <FieldError field={`schedule_where-${row.rowId}`} error={validation.errors[`schedule_where-${row.rowId}`]} />
                        </label>
                      </>
                    )}
                    <label className="param-field">
                      <span>{t("setup.extras.remark")}</span>
                      <input {...fieldProps("remark", row.remark ?? "", (value) => ({ remark: value }))} />
                      <FieldError field={`remark-${row.rowId}`} error={validation.errors[`remark-${row.rowId}`]} />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.extras.optionLabel")}
                        <HelpHint text={t("setup.extras.optionLabelHint")} />
                      </span>
                      <input {...fieldProps("option_label", row.option_label ?? "", (value) => ({ option_label: value }))} />
                      <FieldError field={`option_label-${row.rowId}`} error={validation.errors[`option_label-${row.rowId}`]} />
                    </label>
                    {row.option_label && (
                      <label className="param-field">
                        <span>
                          {t("setup.extras.optionChoices")}
                          <HelpHint text={t("setup.extras.optionChoicesHint")} />
                        </span>
                        <input
                          value={row.optionChoicesText}
                          onChange={(event) =>
                            patchRow(row.rowId, {
                              optionChoicesText: event.target.value,
                              option_choices: splitChoices(event.target.value),
                            })
                          }
                        />
                      </label>
                    )}
                  </div>
                  {row.error && <span className="login-error">{row.error}</span>}
                </td>
              </tr>
            </Fragment>
            );
          })}
        </tbody>
      </table>
      <button className="link-button" onClick={addRow}>
        + {t("setup.extras.add")}
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
