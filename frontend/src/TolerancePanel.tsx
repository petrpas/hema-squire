import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type TournamentDetail } from "./api";
import FieldError, { invalidProps } from "./FieldError";
import HelpHint from "./HelpHint";
import { parseInteger } from "./numeric";
import { useFieldValidation } from "./useFieldValidation";
import { apiErrors, checkPercent } from "./validation";

/** The one genuine operation parameter of the payments phase: the amount
 *  tolerance matching compares against. It stays in the console rather than
 *  Setup because it is tuned against transactions that already exist, while
 *  reconciliation is running — not decided before publication (design
 *  regroup-setup-parameters Decision 8).
 *
 *  Its own card rather than part of the flagged queue, which
 *  `add-payments-console-ui` narrows to that queue alone. */
export default function TolerancePanel({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  // what a widened tolerance would now let through, and what came of doing it
  const [resettleable, setResettleable] = useState(0);
  const [settled, setSettled] = useState<number | null>(null);
  const validation = useFieldValidation();
  const fieldRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (detail === null) return;
    setValue(String(detail.amount_tolerance_percent));
    validation.clearAll();
    setDirty(false);
  }, [detail, validation.clearAll]);

  const check = () => checkPercent("amount_tolerance_percent", value);

  const countResettleable = useCallback(() => {
    api.resettleablePayments(slug).then(
      (body) => setResettleable(body.resettleable),
      () => setResettleable(0),
    );
  }, [slug]);

  // re-read whenever the saved tolerance changes, which is what moves the
  // number: `detail` arrives again after every save
  useEffect(countResettleable, [countResettleable, detail?.amount_tolerance_percent]);

  async function resettle() {
    setBusy(true);
    try {
      const body = await api.resettlePayments(slug);
      setSettled(body.settled);
      countResettleable();
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  if (detail === null) return null;

  async function save() {
    if (validation.validateAll([check]) > 0) {
      fieldRef.current?.focus();
      return;
    }
    setBusy(true);
    try {
      const parsed = parseInteger(value);
      await api.updateTournament(slug, {
        amount_tolerance_percent: parsed.ok ? parsed.value : null,
      });
      setDirty(false);
      setSettled(null);
      onSaved();
    } catch (err) {
      validation.applyApiErrors(apiErrors(err));
    } finally {
      setBusy(false);
    }
  }

  const title = t("payments.tolerance.title");

  return (
    <section className="rail-card tolerance-card">
      {/* One heading, not a heading and a field label repeating it: the card
          holds a single parameter, so its name and the field's name were the
          same words twice. The hint hangs off the heading for the same
          reason. */}
      <h2>
        {title}
        <HelpHint text={t("payments.tolerance.hint")} align="center" />
      </h2>
      <div className="tolerance-row">
        <input
          ref={fieldRef}
          type="text"
          inputMode="numeric"
          aria-label={title}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setDirty(true);
            validation.clearIfValid("amount_tolerance_percent", check);
          }}
          onBlur={() => validation.touch("amount_tolerance_percent", check)}
          {...invalidProps("amount_tolerance_percent", validation.errors.amount_tolerance_percent)}
        />
        {/* Beside the field rather than under it, and marked rather than
            labelled: one parameter does not need a full-width bar reading
            "save" below it. The name stays on the control for anything not
            reading the shape. */}
        <button
          type="button"
          className="secondary tolerance-save"
          onClick={() => void save()}
          disabled={!dirty || busy}
          aria-label={t("rail.save")}
          title={t("rail.save")}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
            <path d="M3 8.5 6.5 12 13 4.5" />
          </svg>
        </button>
      </div>
      <FieldError
        field="amount_tolerance_percent"
        error={validation.errors.amount_tolerance_percent}
      />

      {/* The number before the act, not after it. A widened tolerance reaches
          payments that are already in — it settles reservations and mails the
          fencers — so the organizer commits to a count rather than discovering
          one (spec payments, Re-deciding a short payment). Saving alone changes
          nothing that already happened. */}
      {resettleable > 0 && !dirty && (
        <>
          <p className="rail-hint instead-of-control">
            {t("payments.tolerance.resettleable", { count: resettleable })}
          </p>
          <button
            type="button"
            className="secondary param-save"
            onClick={() => void resettle()}
            disabled={busy}
          >
            {t("payments.tolerance.resettle")}
          </button>
        </>
      )}
      {settled !== null && (
        <p className="rail-hint">{t("payments.tolerance.settled", { count: settled })}</p>
      )}
    </section>
  );
}
