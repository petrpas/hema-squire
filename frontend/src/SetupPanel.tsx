import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  type Discount,
  type DiscountCondition,
  type DiscountEffect,
  type ExtraCategory,
  type ExtraItem,
  type TournamentDetail,
  api,
} from "./api";

const EXTRA_CATEGORIES: ExtraCategory[] = ["seminar", "rental", "afterparty", "merch"];

// Identity fields patched as a whole, mirroring ParamPanel's save pattern
// but for the fields that live in the Setup tab's main content, not the rail.
const IDENTITY_FIELDS = [
  { key: "display_name", type: "text" },
  { key: "date", type: "date" },
  { key: "location", type: "text" },
  { key: "language", type: "text" },
  { key: "registration_opens", type: "date" },
  { key: "registration_closes", type: "date" },
] as const;

function IdentitySection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const field of IDENTITY_FIELDS) {
      const value = detail[field.key];
      next[field.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(next);
    setDirty(false);
  }, [detail]);

  async function save() {
    setBusy(true);
    try {
      const patch: Record<string, unknown> = {};
      for (const field of IDENTITY_FIELDS) {
        const raw = values[field.key] ?? "";
        patch[field.key] = raw === "" ? null : raw;
      }
      await api.updateTournament(slug, patch);
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.identity.title")}</h2>
      <div className="param-fields">
        {IDENTITY_FIELDS.map((field) => (
          <label key={field.key} className="param-field">
            <span>{t(`param.${field.key}`)}</span>
            <input
              type={field.type}
              value={values[field.key] ?? ""}
              onChange={(event) => {
                setValues({ ...values, [field.key]: event.target.value });
                setDirty(true);
              }}
            />
          </label>
        ))}
      </div>
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function OrganizersSection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [names, setNames] = useState<string[]>(detail.organizer_names);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setNames(detail.organizer_names);
    setDirty(false);
  }, [detail]);

  async function save() {
    setBusy(true);
    try {
      await api.updateTournament(slug, {
        organizer_names: names.map((n) => n.trim()).filter((n) => n.length > 0),
      });
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.organizers.title")}</h2>
      <table className="sheet-table">
        <tbody>
          {names.map((name, index) => (
            <tr key={index}>
              <td>
                <input
                  className="cell-input"
                  value={name}
                  placeholder={t("setup.organizers.placeholder")}
                  onChange={(event) => {
                    const next = [...names];
                    next[index] = event.target.value;
                    setNames(next);
                    setDirty(true);
                  }}
                />
              </td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  onClick={() => {
                    setNames(names.filter((_, i) => i !== index));
                    setDirty(true);
                  }}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="secondary param-save"
        onClick={() => {
          setNames([...names, ""]);
          setDirty(true);
        }}
      >
        + {t("setup.organizers.add")}
      </button>
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function DisciplinesSection({
  detail,
  slug,
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, { capacity: string; fee: string }>>({});
  const [newCode, setNewCode] = useState("");
  const [newCapacity, setNewCapacity] = useState("");
  const [newFee, setNewFee] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.taxonomy().then(setTaxonomy, () => setTaxonomy({}));
  }, []);

  useEffect(() => {
    const next: Record<string, { capacity: string; fee: string }> = {};
    for (const d of detail.disciplines) {
      next[d.code] = { capacity: String(d.capacity), fee: d.fee === null ? "" : String(d.fee) };
    }
    setDrafts(next);
  }, [detail]);

  function dirty(code: string): boolean {
    const original = detail.disciplines.find((d) => d.code === code);
    const draft = drafts[code];
    if (!original || !draft) return false;
    return (
      String(original.capacity) !== draft.capacity ||
      (original.fee === null ? "" : String(original.fee)) !== draft.fee
    );
  }

  async function saveRow(code: string) {
    const draft = drafts[code];
    setBusy(true);
    try {
      await api.updateDiscipline(slug, code, {
        code,
        capacity: Number(draft.capacity),
        fee: draft.fee === "" ? null : Number(draft.fee),
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function removeRow(code: string) {
    setBusy(true);
    try {
      await api.deleteDiscipline(slug, code);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function addRow() {
    setBusy(true);
    try {
      await api.addDiscipline(slug, {
        code: newCode,
        capacity: Number(newCapacity),
        fee: newFee === "" ? null : Number(newFee),
      });
      setNewCode("");
      setNewCapacity("");
      setNewFee("");
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  const usedCodes = new Set(detail.disciplines.map((d) => d.code));
  const availableCodes = Object.keys(taxonomy).filter((code) => !usedCodes.has(code));

  return (
    <section className="rail-card">
      <h2>{t("setup.disciplines.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.disciplines.code")}</th>
            <th>{t("setup.disciplines.capacity")}</th>
            <th>{t("setup.disciplines.fee")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {detail.disciplines.map((d) => (
            <tr key={d.code}>
              <td>
                {d.code} — {d.name}
              </td>
              <td>
                <input
                  className="cell-input"
                  type="number"
                  min={1}
                  value={drafts[d.code]?.capacity ?? ""}
                  onChange={(event) =>
                    setDrafts({
                      ...drafts,
                      [d.code]: { ...drafts[d.code], capacity: event.target.value },
                    })
                  }
                />
              </td>
              <td>
                <input
                  className="cell-input"
                  type="number"
                  min={0}
                  value={drafts[d.code]?.fee ?? ""}
                  onChange={(event) =>
                    setDrafts({
                      ...drafts,
                      [d.code]: { ...drafts[d.code], fee: event.target.value },
                    })
                  }
                />
              </td>
              <td className="col-actions">
                {dirty(d.code) && (
                  <button
                    className="row-action"
                    title={t("rail.save")}
                    disabled={busy}
                    onClick={() => void saveRow(d.code)}
                  >
                    ✓
                  </button>
                )}
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  disabled={busy}
                  onClick={() => void removeRow(d.code)}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <select value={newCode} onChange={(event) => setNewCode(event.target.value)}>
                <option value="">—</option>
                {availableCodes.map((code) => (
                  <option key={code} value={code}>
                    {code} — {taxonomy[code]}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <input
                className="cell-input"
                type="number"
                min={1}
                value={newCapacity}
                onChange={(event) => setNewCapacity(event.target.value)}
              />
            </td>
            <td>
              <input
                className="cell-input"
                type="number"
                min={0}
                value={newFee}
                onChange={(event) => setNewFee(event.target.value)}
              />
            </td>
            <td className="col-actions">
              <button
                className="row-action"
                title={t("setup.disciplines.add")}
                disabled={busy || !newCode || !newCapacity}
                onClick={() => void addRow()}
              >
                +
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

function ExtraItemsSection({
  detail,
  slug,
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Record<number, ExtraItem>>({});
  const [newItem, setNewItem] = useState({
    name: "",
    category: "rental" as ExtraCategory,
    price: "",
    max_qty: "1",
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const next: Record<number, ExtraItem> = {};
    for (const item of detail.extra_items) next[item.id] = { ...item };
    setDrafts(next);
  }, [detail]);

  function dirty(item: ExtraItem): boolean {
    const draft = drafts[item.id];
    if (!draft) return false;
    return (
      draft.name !== item.name ||
      draft.category !== item.category ||
      draft.price !== item.price ||
      draft.max_qty !== item.max_qty
    );
  }

  async function saveRow(id: number) {
    const draft = drafts[id];
    setBusy(true);
    try {
      await api.updateExtraItem(slug, id, {
        name: draft.name,
        category: draft.category,
        price: draft.price,
        max_qty: draft.max_qty,
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function removeRow(id: number) {
    setBusy(true);
    try {
      await api.deleteExtraItem(slug, id);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function addRow() {
    setBusy(true);
    try {
      await api.addExtraItem(slug, {
        name: newItem.name,
        category: newItem.category,
        price: Number(newItem.price),
        max_qty: Number(newItem.max_qty) || 1,
      });
      setNewItem({ name: "", category: "rental", price: "", max_qty: "1" });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.extras.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.extras.name")}</th>
            <th>{t("setup.extras.category")}</th>
            <th>{t("setup.extras.price")}</th>
            <th>{t("setup.extras.maxQty")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {detail.extra_items.map((item) => {
            const draft = drafts[item.id] ?? item;
            return (
              <tr key={item.id}>
                <td>
                  <input
                    className="cell-input"
                    value={draft.name}
                    onChange={(event) =>
                      setDrafts({ ...drafts, [item.id]: { ...draft, name: event.target.value } })
                    }
                  />
                </td>
                <td>
                  <select
                    value={draft.category}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [item.id]: {
                          ...draft,
                          category: event.target.value as ExtraCategory,
                        },
                      })
                    }
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
                    type="number"
                    min={0}
                    value={draft.price}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [item.id]: { ...draft, price: Number(event.target.value) },
                      })
                    }
                  />
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={1}
                    value={draft.max_qty}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [item.id]: { ...draft, max_qty: Number(event.target.value) },
                      })
                    }
                  />
                </td>
                <td className="col-actions">
                  {dirty(item) && (
                    <button
                      className="row-action"
                      title={t("rail.save")}
                      disabled={busy}
                      onClick={() => void saveRow(item.id)}
                    >
                      ✓
                    </button>
                  )}
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    disabled={busy}
                    onClick={() => void removeRow(item.id)}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            );
          })}
          <tr>
            <td>
              <input
                className="cell-input"
                value={newItem.name}
                onChange={(event) => setNewItem({ ...newItem, name: event.target.value })}
              />
            </td>
            <td>
              <select
                value={newItem.category}
                onChange={(event) =>
                  setNewItem({ ...newItem, category: event.target.value as ExtraCategory })
                }
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
                type="number"
                min={0}
                value={newItem.price}
                onChange={(event) => setNewItem({ ...newItem, price: event.target.value })}
              />
            </td>
            <td>
              <input
                className="cell-input"
                type="number"
                min={1}
                value={newItem.max_qty}
                onChange={(event) => setNewItem({ ...newItem, max_qty: event.target.value })}
              />
            </td>
            <td className="col-actions">
              <button
                className="row-action"
                title={t("setup.extras.add")}
                disabled={busy || !newItem.name || !newItem.price}
                onClick={() => void addRow()}
              >
                +
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

function emptyDiscount(): Discount {
  return {
    name: "",
    condition: { kind: "discipline_count", count: 2 },
    effect: { kind: "fixed", value: 0 },
    scope: ["discipline"],
  };
}

function DiscountsSection({
  detail,
  slug,
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Discount[]>(detail.discounts);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

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

  async function save() {
    setBusy(true);
    try {
      await api.updateTournament(slug, { discounts: drafts });
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

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
          {drafts.map((discount, index) => (
            <tr key={index}>
              <td>
                <input
                  className="cell-input"
                  value={discount.name}
                  onChange={(event) => update(index, { name: event.target.value })}
                />
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
                    <input
                      className="cell-input"
                      type="number"
                      min={1}
                      value={discount.condition.count ?? ""}
                      onChange={(event) =>
                        updateCondition(index, { count: Number(event.target.value) })
                      }
                    />
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
                    onChange={(event) =>
                      updateEffect(index, { kind: event.target.value as DiscountEffect["kind"] })
                    }
                  >
                    <option value="fixed">{t("setup.discounts.fixed")}</option>
                    <option value="percent">{t("setup.discounts.percent")}</option>
                  </select>
                  <input
                    className="cell-input"
                    type="number"
                    min={0}
                    value={discount.effect.value}
                    onChange={(event) =>
                      updateEffect(index, { value: Number(event.target.value) })
                    }
                  />
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
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="secondary param-save"
        onClick={() => {
          setDrafts([...drafts, emptyDiscount()]);
          setDirty(true);
        }}
      >
        + {t("setup.discounts.add")}
      </button>
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function ChecklistSection({ detail }: { detail: TournamentDetail }) {
  const { t } = useTranslation();
  const missing = detail.setup_missing ?? [];
  return (
    <section className="rail-card dashed">
      <h2>{t("setup.checklist.title")}</h2>
      {missing.length === 0 ? (
        <p className="rail-hint">{t("setup.checklist.ready")}</p>
      ) : (
        <div className="chips">
          {missing.map((key) => (
            <span key={key} className="chip">
              {t(`setup.missing.${key}`)}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

export default function SetupPanel({
  detail,
  slug,
  onSaved,
  hasRegistrations,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
  hasRegistrations: boolean;
}) {
  const { t } = useTranslation();
  if (detail === null) return <p>{t("common.loading")}</p>;

  return (
    <div className="setup-panel">
      <ChecklistSection detail={detail} />
      <IdentitySection detail={detail} slug={slug} onSaved={onSaved} />
      <OrganizersSection detail={detail} slug={slug} onSaved={onSaved} />
      <DisciplinesSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
      <ExtraItemsSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
      <DiscountsSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
    </div>
  );
}
