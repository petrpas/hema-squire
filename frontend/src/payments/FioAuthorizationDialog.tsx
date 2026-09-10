import { useTranslation } from "react-i18next";

import Modal from "../Modal";

/** What the bank said when a poll reached past its ninety-day history, and the
 *  three things the organizer can do about it.
 *
 *  A dialog rather than a line of error text because the answer is not one the
 *  console can pick. Fio serves the last ninety days to any valid token and
 *  refuses everything earlier until the token's full history is unlocked by a
 *  strong authorization in internet banking, which then holds for ten minutes.
 *  Nothing in the API can ask for that, so the organizer either goes and does
 *  it, settles for the part of the window the bank will serve unasked, or
 *  leaves it — and which of those is right depends on where the money is.
 *
 *  Its own file, and not a branch inside `IntakePanel`: the panel orchestrates
 *  three intake actions and has no room to also hold the bank's rules.
 */
export default function FioAuthorizationDialog({
  since,
  windowFrom,
  windowTo,
  onPartial,
  onRetry,
  onClose,
}: {
  /** The first day the bank will serve without the unlock — its own date, from
   *  its own refusal. */
  since: string;
  /** The window the poll asked about: the tournament's own. */
  windowFrom: string;
  windowTo: string;
  /** Poll again from `since` instead. Offered only where that still covers a
   *  day of the window. */
  onPartial: () => void;
  /** Poll the whole window again, the organizer having authorized it. */
  onRetry: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const day = (value: string) => new Date(value).toLocaleDateString("cs");
  // where the bank's boundary falls past the end of the window, no day of this
  // tournament is inside the ninety days, and the shortened poll would ask
  // about days the tournament had already ended before. Stating that beats
  // offering a button that comes back with nothing (spec payments-intake)
  const overlaps = since <= windowTo;

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("payments.intake.lock.title")}</h2>
        <p className="rail-hint">
          {t("payments.intake.lock.window", {
            from: day(windowFrom),
            to: day(windowTo),
            since: day(since),
          })}
        </p>
        <p className="rail-hint">{t("payments.intake.lock.how")}</p>
        <p className="rail-hint">
          {overlaps
            ? t("payments.intake.lock.partialCovers", { since: day(since) })
            : t("payments.intake.lock.noOverlap", { to: day(windowTo) })}
        </p>

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          {overlaps && (
            <button type="button" className="secondary" onClick={onPartial}>
              {t("payments.intake.lock.partial", { since: day(since) })}
            </button>
          )}
          <button type="button" className="btn-primary" onClick={onRetry}>
            {t("payments.intake.lock.authorized")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
