import { IconEdit, IconX } from "@tabler/icons-react";
import { Fragment, type ChangeEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Currency,
  type Discipline,
  type DisciplineGender,
  type DisciplineInput,
  type DisciplineKind,
  type DisciplineMaterial,
  type TournamentDetail,
  api,
} from "../api";
import { DISCIPLINE_CAPACITY_MAX } from "../constraints";
import DisciplineDialog, { type DisciplineIdentity } from "../DisciplineDialog";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { showsEur } from "../money";
import { parseInteger } from "../numeric";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkMoney, checkNumeric, checkString, checkUrl, type FieldError as FieldErrorValue } from "../validation";
import {
  _int,
  recalculateMissing,
  type SaverRegistry,
  type SaveOutcome,
  TAXONOMY_WEAPON_CODES,
  useSectionSaver,
} from "./shared";

type DisciplineDraft = {
  slug: string;
  name: string;
  weapon: string;
  gender: DisciplineGender;
  material: DisciplineMaterial;
  kind: DisciplineKind;
  team_min: string;
  team_max: string;
  capacity: string;
  fee: string;
  fee_eur: string;
  schedule_when: string;
  schedule_where: string;
  ruleset_name: string;
  ruleset_url: string;
};

type DisciplineRow = DisciplineDraft & {
  rowId: string;
  isNew: boolean;
  error: string | null;
  // UI-only: whether the weapon field shows the free-text "other" input
  // rather than the taxonomy select (design discipline-identity D4)
  weaponCustom: boolean;
  // The slug the server knows this row by, unchanged by editing `slug`
  // (design discipline-identity-modal D7) — lookups and the PATCH path
  // resolve by this, never by the (now editable) `slug` field.
  originalSlug: string;
  identityFrozen: boolean;
};

function disciplineToRow(d: Discipline): DisciplineRow {
  return {
    rowId: d.slug,
    slug: d.slug,
    originalSlug: d.slug,
    identityFrozen: d.identity_frozen,
    name: d.name,
    weapon: d.weapon,
    gender: d.gender,
    material: d.material,
    weaponCustom: !TAXONOMY_WEAPON_CODES.includes(d.weapon),
    isNew: false,
    error: null,
    kind: d.kind,
    team_min: d.team_min === null ? "" : String(d.team_min),
    team_max: d.team_max === null ? "" : String(d.team_max),
    capacity: String(d.capacity),
    fee: d.fee === null ? "" : String(d.fee),
    fee_eur: d.fee_eur === null ? "" : String(d.fee_eur),
    schedule_when: d.schedule_when ?? "",
    schedule_where: d.schedule_where ?? "",
    ruleset_name: d.ruleset_name ?? "",
    ruleset_url: d.ruleset_url ?? "",
  };
}

function disciplineRowDirty(row: DisciplineRow, detail: TournamentDetail): boolean {
  const original = detail.disciplines.find((d) => d.slug === row.originalSlug);
  if (!original) return false;
  return (
    original.slug !== row.slug ||
    original.name !== row.name ||
    original.weapon !== row.weapon ||
    original.gender !== row.gender ||
    original.material !== row.material ||
    original.kind !== row.kind ||
    (original.team_min === null ? "" : String(original.team_min)) !== row.team_min ||
    (original.team_max === null ? "" : String(original.team_max)) !== row.team_max ||
    String(original.capacity) !== row.capacity ||
    (original.fee === null ? "" : String(original.fee)) !== row.fee ||
    (original.fee_eur === null ? "" : String(original.fee_eur)) !== row.fee_eur ||
    (original.schedule_when ?? "") !== row.schedule_when ||
    (original.schedule_where ?? "") !== row.schedule_where ||
    (original.ruleset_name ?? "") !== row.ruleset_name ||
    (original.ruleset_url ?? "") !== row.ruleset_url
  );
}

function disciplineRowInput(row: DisciplineRow): DisciplineInput {
  return {
    slug: row.slug || null,
    name: row.name || null,
    weapon: row.weapon,
    gender: row.gender,
    material: row.material,
    kind: row.kind,
    team_min: row.kind === "team" ? _int(row.team_min) : null,
    team_max: row.kind === "team" ? _int(row.team_max) : null,
    capacity: _int(row.capacity) ?? 0,
    fee: row.fee === "" ? null : _int(row.fee),
    fee_eur: row.fee_eur === "" ? null : _int(row.fee_eur),
    schedule_when: row.schedule_when || null,
    schedule_where: row.schedule_where || null,
    ruleset_name: row.ruleset_name || null,
    ruleset_url: row.ruleset_url || null,
  };
}

/** Per-field checks for one discipline row. Each error's `field` is scoped
 * with the row id (`"capacity-<rowId>"`) so multiple rows' errors coexist in
 * one `useFieldValidation` instance without colliding — a bare backend
 * rejection field is rescoped the same way when a flush fails (design D3,
 * task 6.1/6.4). */
function disciplineRowChecks(
  row: DisciplineRow,
  currency: Currency,
): Record<string, () => FieldErrorValue | null> {
  const scoped = (field: string) => `${field}-${row.rowId}`;
  return {
    capacity: () => {
      const key = scoped("capacity");
      const basic = checkNumeric(key, "DisciplineIn.capacity", row.capacity, { required: true });
      if (basic) return basic;
      const ceiling = DISCIPLINE_CAPACITY_MAX[row.kind];
      const parsed = parseInteger(row.capacity);
      if (parsed.ok && parsed.value > ceiling) {
        return { field: key, code: "out_of_range", params: { min: 1, max: ceiling } };
      }
      return null;
    },
    fee: () => checkMoney(scoped("fee"), row.fee, currency),
    fee_eur: () => checkMoney(scoped("fee_eur"), row.fee_eur, "EUR"),
    team_min: () =>
      row.kind === "team"
        ? checkNumeric(scoped("team_min"), "DisciplineIn.team_min", row.team_min, { required: true })
        : null,
    team_max: () => {
      if (row.kind !== "team") return null;
      const maxError = checkNumeric(scoped("team_max"), "DisciplineIn.team_max", row.team_max, {
        required: true,
      });
      if (maxError) return maxError;
      const min = parseInteger(row.team_min);
      const max = parseInteger(row.team_max);
      if (min.ok && max.ok && max.value < min.value) {
        return { field: scoped("team_max"), code: "out_of_range", params: { min: min.value } };
      }
      return null;
    },
    schedule_when: () =>
      checkString(scoped("schedule_when"), "DisciplineIn.schedule_when", row.schedule_when),
    schedule_where: () =>
      checkString(scoped("schedule_where"), "DisciplineIn.schedule_where", row.schedule_where),
    ruleset_name: () =>
      checkString(scoped("ruleset_name"), "DisciplineIn.ruleset_name", row.ruleset_name),
    ruleset_url: () => checkUrl(scoped("ruleset_url"), "DisciplineIn.ruleset_url", row.ruleset_url),
  };
}

// The price-change warning is about prices specifically, not any edit to a
// row (schedule/ruleset changes are informational, not pricing) — a new row
// necessarily introduces a price, so it always counts.
function disciplineRowTouchesPrice(row: DisciplineRow, detail: TournamentDetail): boolean {
  if (row.isNew) return true;
  const original = detail.disciplines.find((d) => d.slug === row.originalSlug);
  if (!original) return false;
  return (
    (original.fee === null ? "" : String(original.fee)) !== row.fee ||
    (original.fee_eur === null ? "" : String(original.fee_eur)) !== row.fee_eur
  );
}

function blankDisciplineRow(rowId: string): DisciplineRow {
  return {
    rowId,
    slug: "",
    originalSlug: "",
    identityFrozen: false,
    name: "",
    weapon: "",
    gender: "",
    material: "",
    weaponCustom: false,
    isNew: true,
    error: null,
    kind: "individual",
    team_min: "",
    team_max: "",
    capacity: "",
    fee: "",
    fee_eur: "",
    schedule_when: "",
    schedule_where: "",
    ruleset_name: "",
    ruleset_url: "",
  };
}

export function DisciplinesSection({
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
  const [rows, setRows] = useState<DisciplineRow[]>(() => detail.disciplines.map(disciplineToRow));
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  // "new" opens the dialog for a discipline not yet in the table (design
  // discipline-identity-modal: "a row exists only once the dialog is
  // confirmed"); a rowId reopens the dialog on that existing row.
  const [dialogRowId, setDialogRowId] = useState<string | "new" | null>(null);
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);
  const nextTempId = useRef(0);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const rowsRef = useRef(rows);
  rowsRef.current = rows;
  const removedRef = useRef(removed);
  removedRef.current = removed;

  // Below the table, shown only while a team row exists in the current draft
  // — including one added but not yet saved (design setup-navigation:
  // "Deadline appears with the first team row"). Written by this same tab's
  // save control, as its own registry entry alongside the table (task 8.2).
  const [deadline, setDeadline] = useState(detail.team_composition_deadline ?? "");
  const [deadlineDirty, setDeadlineDirty] = useState(false);
  const hasTeamRow = rows.some((row) => row.kind === "team");

  useEffect(() => {
    setDeadline(detail.team_composition_deadline ?? "");
    setDeadlineDirty(false);
  }, [detail]);

  useSectionSaver(registry, "disciplines", "compositionDeadline", {
    pendingCount: deadlineDirty ? 1 : 0,
    touchesPrice: false,
    validate: () => 0,
    focusFirstInvalid: () => {},
    flush: async () => {
      try {
        await api.updateTournament(slug, {
          team_composition_deadline: deadline || null,
        });
        setDeadlineDirty(false);
        return [{ change: "team_composition_deadline", section: "disciplines", error: null }];
      } catch (err) {
        const message = t("setup.saveBar.genericError", {
          status: err instanceof ApiError ? err.status : "?",
        });
        return [{ change: "team_composition_deadline", section: "disciplines", error: message }];
      }
    },
  });

  // Reseed from the freshly saved detail only while the section holds no
  // pending changes, so a refetch triggered by another tab's save (or by
  // this tab's own save) cannot stomp still-pending drafts (D8).
  useEffect(() => {
    const clean =
      removedRef.current.size === 0 &&
      rowsRef.current.every((row) => !row.isNew && !disciplineRowDirty(row, detail));
    if (clean) {
      setRows(detail.disciplines.map(disciplineToRow));
      setRemoved(new Set());
    }
  }, [detail]);

  function patchRow(rowId: string, patch: Partial<DisciplineRow>) {
    setRows((prev) => prev.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)));
  }

  function removeRow(row: DisciplineRow) {
    setRows((prev) => prev.filter((r) => r.rowId !== row.rowId));
    // the server knows this row by its original slug, not a possibly-edited
    // draft one (design discipline-identity-modal D7)
    if (!row.isNew) setRemoved((prev) => new Set(prev).add(row.originalSlug));
  }

  function rowIdentity(row: DisciplineRow): DisciplineIdentity {
    return {
      kind: row.kind,
      weapon: row.weapon,
      weaponCustom: row.weaponCustom,
      gender: row.gender,
      material: row.material,
      name: row.name,
      slug: row.slug,
    };
  }

  // Confirming the dialog writes to the local draft only — no addDiscipline
  // or updateDiscipline call here; the tab's save control stays the only
  // writer (design discipline-identity-modal D2, setup-navigation).
  function confirmDialog(identity: DisciplineIdentity) {
    if (dialogRowId === "new") {
      setRows((prev) => [
        ...prev,
        { ...blankDisciplineRow(`new-${nextTempId.current++}`), ...identity },
      ]);
    } else if (dialogRowId !== null) {
      patchRow(dialogRowId, identity);
    }
    setDialogRowId(null);
  }

  function recalculateAll() {
    setRows((prev) =>
      prev.map((row) => {
        const [fee, fee_eur] = recalculateMissing(row.fee, row.fee_eur, rate);
        return { ...row, fee, fee_eur };
      }),
    );
  }

  const pendingDisciplineCount =
    removed.size + rows.filter((row) => row.isNew || disciplineRowDirty(row, detail)).length;

  function allDisciplineChecks(): Array<() => FieldErrorValue | null> {
    return rows.flatMap((row) => Object.values(disciplineRowChecks(row, detail.local_currency)));
  }

  useSectionSaver(registry, "disciplines", "disciplines", {
    pendingCount: pendingDisciplineCount,
    touchesPrice: rows.some((row) => disciplineRowTouchesPrice(row, detail)),
    validate: () => validation.validateAll(allDisciplineChecks()),
    focusFirstInvalid: () => {
      for (const row of rows) {
        for (const [field, check] of Object.entries(disciplineRowChecks(row, detail.local_currency))) {
          if (check()) {
            fieldRefs.current[`${field}-${row.rowId}`]?.focus();
            return;
          }
        }
      }
    },
    flush: async () => {
      const outcomes: SaveOutcome[] = [];
      const stillRemoved = new Set<string>();
      for (const rowSlug of removed) {
        try {
          await api.deleteDiscipline(slug, rowSlug);
          outcomes.push({ change: rowSlug, section: "disciplines", error: null });
        } catch (err) {
          stillRemoved.add(rowSlug);
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          outcomes.push({ change: rowSlug, section: "disciplines", error: message });
        }
      }

      const results = new Map<string, string | null>();
      const created = new Map<string, Discipline>();
      for (const row of rowsRef.current.filter(
        (row) => !row.isNew && disciplineRowDirty(row, detail),
      )) {
        try {
          const saved = await api.updateDiscipline(slug, row.originalSlug, disciplineRowInput(row));
          results.set(row.rowId, null);
          created.set(row.rowId, saved);
          outcomes.push({ change: saved.slug, section: "disciplines", error: null });
        } catch (err) {
          const fieldErrors = apiErrors(err).map((e) => ({ ...e, field: `${e.field}-${row.rowId}` }));
          validation.applyApiErrors(fieldErrors);
          const message =
            fieldErrors.length > 0
              ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
              : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
          results.set(row.rowId, message);
          outcomes.push({ change: row.slug, section: "disciplines", error: message });
        }
      }
      for (const row of rowsRef.current.filter((row) => row.isNew)) {
        try {
          const saved = await api.addDiscipline(slug, disciplineRowInput(row));
          results.set(row.rowId, null);
          created.set(row.rowId, saved);
          outcomes.push({ change: saved.slug, section: "disciplines", error: null });
        } catch (err) {
          const fieldErrors = apiErrors(err).map((e) => ({ ...e, field: `${e.field}-${row.rowId}` }));
          validation.applyApiErrors(fieldErrors);
          const message =
            fieldErrors.length > 0
              ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
              : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
          results.set(row.rowId, message);
          outcomes.push({ change: row.slug || row.name, section: "disciplines", error: message });
        }
      }

      setRemoved(stillRemoved);
      setRows((prev) =>
        prev.map((row) => {
          const result = results.get(row.rowId);
          if (result === undefined) return row;
          if (result !== null) return { ...row, error: result };
          const saved = created.get(row.rowId);
          return saved ? { ...disciplineToRow(saved), rowId: row.rowId } : { ...row, isNew: false, error: null };
        }),
      );
      return outcomes;
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.disciplines.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>
              {t("setup.disciplines.name")}
              <HelpHint text={t("setup.disciplines.nameHint")} />
            </th>
            <th>
              {t("setup.disciplines.slug")}
              <HelpHint text={t("setup.disciplines.slugHint")} />
            </th>
            <th>{t("setup.disciplines.capacity")}</th>
            <th>{t("setup.disciplines.fee", { currency: detail.local_currency })}</th>
            {eur && <th>{t("setup.disciplines.feeEur")}</th>}
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const checks = disciplineRowChecks(row, detail.local_currency);
            function fieldProps<K extends keyof DisciplineRow>(field: string, key: K) {
              const check = checks[field];
              const scopedKey = `${field}-${row.rowId}`;
              return {
                ref: (el: HTMLInputElement | null) => {
                  fieldRefs.current[scopedKey] = el;
                },
                value: row[key] as string,
                onChange: (event: ChangeEvent<HTMLInputElement>) => {
                  patchRow(row.rowId, { [key]: event.target.value } as Partial<DisciplineRow>);
                  validation.clearIfValid(scopedKey, check);
                },
                onBlur: () => validation.touch(scopedKey, check),
                ...invalidProps(scopedKey, validation.errors[scopedKey]),
              };
            }
            return (
            <Fragment key={row.rowId}>
              <tr>
                <td>
                  <strong>{row.name}</strong>
                </td>
                <td>
                  <span className="muted">{row.slug}</span>
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="text"
                    inputMode="numeric"
                    {...fieldProps("capacity", "capacity")}
                  />
                  <span className="muted">
                    {" "}
                    {row.kind === "team"
                      ? t("setup.disciplines.capacityUnitTeam")
                      : t("setup.disciplines.capacityUnitIndividual")}
                  </span>
                  <FieldError field={`capacity-${row.rowId}`} error={validation.errors[`capacity-${row.rowId}`]} />
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="text"
                    inputMode="numeric"
                    {...fieldProps("fee", "fee")}
                  />
                  {row.kind === "team" && (
                    <span className="muted"> {t("setup.disciplines.feeUnitTeam")}</span>
                  )}
                  <FieldError field={`fee-${row.rowId}`} error={validation.errors[`fee-${row.rowId}`]} />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="text"
                      inputMode="numeric"
                      {...fieldProps("fee_eur", "fee_eur")}
                    />
                    <FieldError field={`fee_eur-${row.rowId}`} error={validation.errors[`fee_eur-${row.rowId}`]} />
                  </td>
                )}
                <td className="col-actions">
                  <div className="row-actions">
                    {!row.identityFrozen && (
                      <button
                        className="row-action"
                        title={t("setup.disciplines.reopen")}
                        onClick={() => setDialogRowId(row.rowId)}
                      >
                        <IconEdit size={16} stroke={1.5} />
                      </button>
                    )}
                    <button
                      className="row-action"
                      title={t("actions.delete")}
                      onClick={() => removeRow(row)}
                    >
                      <IconX size={16} stroke={1.5} />
                    </button>
                  </div>
                </td>
              </tr>
              <tr className="detail-subrow">
                <td colSpan={eur ? 6 : 5}>
                  <div className="param-fields">
                    {row.kind === "team" && (
                      <>
                        <label className="param-field">
                          <span>{t("setup.disciplines.teamMin")}</span>
                          <input
                            className="cell-input"
                            type="text"
                            inputMode="numeric"
                            {...fieldProps("team_min", "team_min")}
                          />
                          <FieldError field={`team_min-${row.rowId}`} error={validation.errors[`team_min-${row.rowId}`]} />
                        </label>
                        <label className="param-field">
                          <span>{t("setup.disciplines.teamMax")}</span>
                          <input
                            className="cell-input"
                            type="text"
                            inputMode="numeric"
                            {...fieldProps("team_max", "team_max")}
                          />
                          <FieldError field={`team_max-${row.rowId}`} error={validation.errors[`team_max-${row.rowId}`]} />
                        </label>
                      </>
                    )}
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.when")}
                        <HelpHint text={t("setup.disciplines.whenHint")} />
                      </span>
                      <input {...fieldProps("schedule_when", "schedule_when")} />
                      <FieldError field={`schedule_when-${row.rowId}`} error={validation.errors[`schedule_when-${row.rowId}`]} />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.where")}
                        <HelpHint text={t("setup.disciplines.whereHint")} />
                      </span>
                      <input {...fieldProps("schedule_where", "schedule_where")} />
                      <FieldError field={`schedule_where-${row.rowId}`} error={validation.errors[`schedule_where-${row.rowId}`]} />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetName")}
                        <HelpHint text={t("setup.disciplines.rulesetNameHint")} />
                      </span>
                      <input {...fieldProps("ruleset_name", "ruleset_name")} />
                      <FieldError field={`ruleset_name-${row.rowId}`} error={validation.errors[`ruleset_name-${row.rowId}`]} />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetUrl")}
                        <HelpHint text={t("setup.disciplines.rulesetUrlHint")} />
                      </span>
                      <input {...fieldProps("ruleset_url", "ruleset_url")} />
                      <FieldError field={`ruleset_url-${row.rowId}`} error={validation.errors[`ruleset_url-${row.rowId}`]} />
                    </label>
                  </div>
                  {row.error && <span className="login-error">{row.error}</span>}
                </td>
              </tr>
            </Fragment>
            );
          })}
        </tbody>
      </table>
      <button className="link-button" onClick={() => setDialogRowId("new")}>
        + {t("setup.disciplines.add")}
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
      {hasTeamRow && (
        <label className="param-field">
          <span>
            {t("setup.disciplines.compositionDeadline")}
            <HelpHint text={t("setup.disciplines.compositionDeadlineHint")} />
          </span>
          <input
            type="date"
            value={deadline}
            onChange={(event) => {
              setDeadline(event.target.value);
              setDeadlineDirty(true);
            }}
          />
        </label>
      )}
      {dialogRowId !== null && (
        <DisciplineDialog
          initial={
            dialogRowId === "new"
              ? null
              : rowIdentity(rows.find((row) => row.rowId === dialogRowId)!)
          }
          otherNames={rows.filter((row) => row.rowId !== dialogRowId).map((row) => row.name)}
          otherSlugs={
            new Set(rows.filter((row) => row.rowId !== dialogRowId).map((row) => row.slug))
          }
          onConfirm={confirmDialog}
          onClose={() => setDialogRowId(null)}
        />
      )}
    </section>
  );
}
