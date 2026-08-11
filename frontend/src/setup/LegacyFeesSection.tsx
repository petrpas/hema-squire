import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";

/** Whether the tournament still prices through the superseded fixed
 *  weapon-rental / afterparty parameters — the same condition
 *  `setup.uses_legacy_fixed_fees` applies on the backend. */
export function usesLegacyFixedFees(detail: TournamentDetail): boolean {
  return (
    Boolean(detail.weapon_rental_fee) ||
    detail.weapon_rental_fee_early !== null ||
    Boolean(detail.afterparty_fee) ||
    detail.afterparty_fee_early !== null
  );
}

/** The escape hatch for a tournament stranded on the legacy pricing path: it
 *  cannot enable EUR, so it can be blocked from publication, and the fields
 *  themselves are no longer editable anywhere. Shown only while the condition
 *  holds, so it never becomes a permanent monument to a legacy path (design
 *  regroup-setup-parameters Decision 7).
 *
 *  Clearing is an explicit organizer action: no migration zeroes these, since
 *  that would silently change the price of a live tournament. */
export function LegacyFeesSection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!usesLegacyFixedFees(detail)) return null;

  const currency = detail.local_currency;
  const rows: [string, number | null][] = [
    ["weapon_rental_fee", detail.weapon_rental_fee],
    ["weapon_rental_fee_early", detail.weapon_rental_fee_early],
    ["afterparty_fee", detail.afterparty_fee],
    ["afterparty_fee_early", detail.afterparty_fee_early],
  ];

  async function clear() {
    setBusy(true);
    setError(null);
    try {
      await api.updateTournament(slug, {
        weapon_rental_fee: 0,
        weapon_rental_fee_early: null,
        afterparty_fee: 0,
        afterparty_fee_early: null,
        early_bird_until: null,
      });
      onSaved();
    } catch (err) {
      setError(
        t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" }),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.legacyFees.title")}</h2>
      <p className="rail-hint">{t("setup.legacyFees.explanation")}</p>
      <ul className="detail-list">
        {rows.map(([key, value]) => (
          <li key={key}>
            {t(`param.${key}`, { currency })}: {value === null ? "—" : value}
          </li>
        ))}
        {detail.early_bird_until !== null && (
          <li>
            {t("param.early_bird_until")}: {detail.early_bird_until}
          </li>
        )}
      </ul>
      <button type="button" className="secondary" disabled={busy} onClick={() => void clear()}>
        {t("setup.legacyFees.clear")}
      </button>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
