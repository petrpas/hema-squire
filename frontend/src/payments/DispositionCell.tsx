import { useTranslation } from "react-i18next";

import type { UncreditedPayment } from "../api";
import { formatMoney } from "../money";

/** What is to be done with a payment that lies on nobody.
 *
 *  One column carrying what three queues used to carry by existing. A proposal,
 *  a refusal and a payment nothing could be read from are not three kinds of
 *  row — they are one row with three things it might say about itself, and
 *  splitting them into tabs meant a reader had to visit three tables to learn
 *  whether there was any work at all.
 *
 *  The evidence stays in the row's own columns: the payer, the amount, the
 *  date, the message. This states the conclusion, and the actions beside it
 *  follow from what it says.
 */
export default function DispositionCell({ payment }: { payment: UncreditedPayment }) {
  const { t } = useTranslation();

  if (payment.disposition === "proposal") {
    return (
      <>
        <strong>{payment.proposed_fencer_name ?? "—"}</strong>
        {/* what they still owe, so the organizer confirms against a balance
            rather than against a name (spec name-assisted-matching) */}
        {payment.proposed_outstanding !== null && (
          <span className="muted">
            {" "}
            {t("payments.uncredited.owes", {
              amount: formatMoney(payment.proposed_outstanding, payment.currency as "CZK" | "EUR"),
            })}
          </span>
        )}
      </>
    );
  }

  if (payment.disposition === "paired_uncredited") {
    // money assigned to somebody it could not reach. The somebody is the first
    // thing the row has to say, because the organizer's next move is to decide
    // whether the pairing was wrong or the registration was
    return (
      <span>
        {t("payments.uncredited.pairedUncredited", {
          names: payment.paired_registrations.map((named) => named.fencer_name).join(", "),
        })}
      </span>
    );
  }

  if (payment.disposition === "refused") {
    const reason = payment.status_reason;
    return (
      <span>
        {reason ? t(`payments.flagged.reasons.${reason}`, { defaultValue: reason }) : "—"}
        {/* what already settled the registration, where a person did: the
            organizer is deciding whether this is further money or the same
            money arriving twice, and that needs the earlier act in front of
            them */}
        {payment.settled_by_hand_reason && (
          <span className="muted">
            {" "}
            {t("payments.flagged.settledByHand", { reason: payment.settled_by_hand_reason })}
          </span>
        )}
        {payment.settled_by_recorded_payment && (
          <span className="muted">
            {" "}
            {t("payments.flagged.settledByPayment", {
              amount: formatMoney(
                payment.settled_by_recorded_payment.amount,
                payment.settled_by_recorded_payment.currency,
              ),
              date: new Date(payment.settled_by_recorded_payment.received_on).toLocaleDateString(
                "cs",
              ),
            })}
          </span>
        )}
      </span>
    );
  }

  // nothing could be read from it at all, which is not a fault and is not
  // stated as one: the row's own evidence is what the organizer works from
  return <span className="muted">—</span>;
}
