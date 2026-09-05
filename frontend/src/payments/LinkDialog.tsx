import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Currency,
  type RankedFencer,
  type Transaction,
  api,
} from "../api";
import { formatMoney } from "../money";

/** Linking a payment to the registrations it pays for.
 *
 *  Addressed by **person** first. A variable symbol is a shortcut, not a
 *  registration's identity: about one payment in ten carries none or carries
 *  one that is wrong, and on a tournament whose organizer keeps the roster none
 *  carries one at all. An organizer looking at such a payment knows who it is
 *  for and not what number they were supposed to quote, so the roster is the
 *  first thing offered — every fencer, ordered by how well they match the
 *  payment's own words, with the strongest marked (spec
 *  name-assisted-matching, design Decision 6).
 *
 *  The symbol stays as a second way in, for an organizer who does know the
 *  number: the detected candidates as one-click entries, and a field to type
 *  one into.
 *
 *  Selection is a list, not a single value: one transfer covering several
 *  fencers is what the endpoint's arrays exist for.
 */
export default function LinkDialog({
  slug,
  transaction,
  onLinked,
  onClose,
}: {
  slug: string;
  transaction: Transaction;
  onLinked: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [roster, setRoster] = useState<RankedFencer[] | null>(null);
  const [filter, setFilter] = useState("");
  const [chosen, setChosen] = useState<number[]>([]);
  const [typedVs, setTypedVs] = useState<number[]>([]);
  const [typed, setTyped] = useState("");
  const [unknown, setUnknown] = useState<number[]>([]);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.transactionRoster(slug, transaction.id).then(
      (body) => setRoster(body.fencers),
      () => setRoster([]),
    );
  }, [slug, transaction.id]);

  const listed = useMemo(() => {
    const needle = filter.trim().toLocaleLowerCase();
    const all = roster ?? [];
    if (!needle) return all;
    return all.filter((fencer) => fencer.name.toLocaleLowerCase().includes(needle));
  }, [roster, filter]);

  const byId = useMemo(
    () => new Map((roster ?? []).map((fencer) => [fencer.registration_id, fencer])),
    [roster],
  );
  const offered = transaction.candidate_vs.filter(
    (vs) => !typedVs.includes(vs) && !chosen.some((id) => byId.get(id)?.vs === vs),
  );

  function toggle(registrationId: number) {
    setUnknown([]);
    setChosen((current) =>
      current.includes(registrationId)
        ? current.filter((id) => id !== registrationId)
        : [...current, registrationId],
    );
  }

  /** A symbol typed or picked resolves to its registration where the roster
   *  knows it, so the selection stays one kind of thing; an unrecognised one
   *  is sent as a symbol and the endpoint says so. */
  function addVs(vs: number) {
    setUnknown([]);
    const known = (roster ?? []).find((fencer) => fencer.vs === vs);
    if (known) {
      toggle(known.registration_id);
      return;
    }
    setTypedVs((current) => (current.includes(vs) ? current : [...current, vs]));
  }

  function addTyped() {
    const vs = Number(typed.trim());
    if (!Number.isInteger(vs) || vs <= 0) return;
    addVs(vs);
    setTyped("");
  }

  async function confirm() {
    setBusy(true);
    setUnknown([]);
    setFailed(false);
    try {
      await api.linkTransaction(slug, transaction.id, typedVs, chosen);
      onLinked();
      onClose();
    } catch (error) {
      // the endpoint distinguishes the two: a VS that resolves to nothing is
      // the organizer's to correct, so the dialog stays open with the entry
      // intact; a transaction matched by a concurrent poll is already resolved,
      // so the dialog closes and the queue refreshes (design D3)
      const detail = error instanceof ApiError ? error.detail : null;
      const values =
        detail && typeof detail === "object" && "unknown_vs" in detail
          ? (detail as { unknown_vs: number[] }).unknown_vs
          : null;
      if (values) {
        setUnknown(values);
      } else if (error instanceof ApiError && error.status === 409) {
        onLinked();
        onClose();
        return;
      } else {
        setFailed(true);
      }
    } finally {
      setBusy(false);
    }
  }

  const nothingChosen = chosen.length === 0 && typedVs.length === 0;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={(event) => event.stopPropagation()}>
        <h2>{t("payments.link.title")}</h2>
        <p className="muted link-context">
          {new Date(transaction.date).toLocaleDateString("cs")} ·{" "}
          {transaction.payer_name ?? t("payments.link.unknownPayer")} ·{" "}
          {formatMoney(transaction.amount_cents / 100, transaction.currency as Currency)}
        </p>
        {transaction.message && <p className="link-message">{transaction.message}</p>}

        <p className="rail-hint">{t("payments.link.roster")}</p>
        <input
          autoFocus
          className="link-filter"
          value={filter}
          placeholder={t("payments.link.search")}
          onChange={(event) => setFilter(event.target.value)}
        />
        {roster === null ? (
          <p className="muted">{t("common.loading")}</p>
        ) : (
          <ul className="link-roster">
            {listed.map((fencer) => (
              <li key={fencer.registration_id}>
                <label className="qualification-option">
                  <input
                    type="checkbox"
                    checked={chosen.includes(fencer.registration_id)}
                    onChange={() => toggle(fencer.registration_id)}
                  />
                  {fencer.name}
                  {fencer.proposed && (
                    <span className="chip">{t("payments.link.strongest")}</span>
                  )}
                  {fencer.rejected && (
                    <span className="muted"> {t("payments.link.refused")}</span>
                  )}
                </label>
                <span className="muted">{fencer.outstanding_amount}</span>
              </li>
            ))}
          </ul>
        )}

        {offered.length > 0 && (
          <>
            <p className="rail-hint">{t("payments.link.candidates")}</p>
            <ul className="link-candidates">
              {offered.map((vs) => (
                <li key={vs}>
                  <button className="row-action" onClick={() => addVs(vs)}>
                    {vs}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="link-entry">
          <input
            value={typed}
            inputMode="numeric"
            placeholder={t("payments.link.placeholder")}
            onChange={(event) => setTyped(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addTyped();
              }
            }}
          />
          <button className="secondary" onClick={addTyped}>
            {t("payments.link.add")}
          </button>
        </div>

        <p className="rail-hint">{t("payments.link.selected")}</p>
        {nothingChosen ? (
          <p className="muted">{t("payments.link.noneSelected")}</p>
        ) : (
          <ul className="link-selected">
            {chosen.map((id) => (
              <li key={`reg-${id}`}>
                {byId.get(id)?.name ?? id}
                <button
                  className="row-action"
                  title={t("payments.link.remove")}
                  onClick={() => toggle(id)}
                >
                  {t("payments.link.remove")}
                </button>
              </li>
            ))}
            {typedVs.map((vs) => (
              <li key={`vs-${vs}`}>
                {vs}
                <button
                  className="row-action"
                  title={t("payments.link.remove")}
                  onClick={() => setTypedVs((c) => c.filter((v) => v !== vs))}
                >
                  {t("payments.link.remove")}
                </button>
              </li>
            ))}
          </ul>
        )}

        {unknown.length > 0 && (
          <p className="login-error">
            {t("payments.link.unknown", { values: unknown.join(", ") })}
          </p>
        )}
        {failed && <p className="login-error">{t("payments.link.failed")}</p>}

        <div className="modal-actions">
          <button className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            className="btn-primary"
            disabled={busy || nothingChosen}
            onClick={() => void confirm()}
          >
            {t("payments.link.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
