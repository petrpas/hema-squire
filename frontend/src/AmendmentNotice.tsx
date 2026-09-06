import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Currency } from "./api";
import { formatMoney } from "./money";

/** What an organizer's discipline correction did beyond the cell.
 *
 *  The disciplines are in front of them; the price and the letter are not, and
 *  both are consequences of the edit they have just made (spec
 *  `discipline-amendment`). Stated once, statically, and leaving by fade-out —
 *  the only departure the design spec allows a confirmation.
 */
export type Amendment = {
  previous_total: string | null;
  total: string | null;
  notified: boolean;
};

/** How long the line stands before it leaves. The same span the operations
 *  indicator uses, so two confirmations of the same console read at one pace. */
const LINGER_MS = 4000;

export default function AmendmentNotice({
  amendment,
  refusal,
  currency,
}: {
  amendment: Amendment | null;
  /** The backend's reason for refusing a correction, where it refused one: an
   *  expired registration, or a field edit where a registration stands behind
   *  the row. Stated in the same place the outcome is, since it answers the
   *  same question — what became of the edit. */
  refusal: string | null;
  /** The tournament's own currency, null until the detail has arrived — the
   *  totals read unitless rather than wrong until it does. */
  currency: Currency | null;
}) {
  const { t } = useTranslation();
  const [leaving, setLeaving] = useState(false);
  const [gone, setGone] = useState(false);

  // The notice is what the props say; the effect only decides when it leaves.
  // Deriving it from state instead would leave the first render empty, which
  // is the one render a static reader ever sees.
  useEffect(() => {
    if (amendment === null && refusal === null) return;
    setLeaving(false);
    setGone(false);
    const fade = window.setTimeout(() => setLeaving(true), LINGER_MS);
    const off = window.setTimeout(() => setGone(true), LINGER_MS * 2);
    return () => {
      window.clearTimeout(fade);
      window.clearTimeout(off);
    };
  }, [amendment, refusal]);

  if (gone) return null;
  const className = `amendment-notice${leaving ? " leaving" : ""}`;
  if (refusal !== null) {
    return (
      <aside className={className} role="status">
        {t(`console.amendment.error.${refusal}`, {
          defaultValue: t("console.amendment.error.failed"),
        })}
      </aside>
    );
  }
  if (amendment === null) return null;
  const shown = amendment;
  const money = (value: string | null) =>
    value === null ? "—" : currency === null ? value : formatMoney(value, currency);

  return (
    <aside className={className} role="status">
      <span>
        {shown.previous_total === shown.total
          ? t("console.amendment.unchanged", { total: money(shown.total) })
          : t("console.amendment.repriced", {
              previous: money(shown.previous_total),
              total: money(shown.total),
            })}
      </span>{" "}
      <span className="muted">
        {shown.notified ? t("console.amendment.notified") : t("console.amendment.silent")}
      </span>
    </aside>
  );
}
