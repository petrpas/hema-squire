import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Queue, QueueDiscipline } from "../api";
import Modal from "../Modal";
import { dayIn } from "../momentText";

/** The Queue phase's rail card: the seating deadline, whether and when seating
 *  settled, the open discipline's free places, and the settle action — here,
 *  beside the rosters it will change (spec seating-queue, Organizer-triggered
 *  seating settlement).
 *
 *  Settling cannot be undone, so it is confirmed first, stating how many
 *  registrations it will move and how many of their teams it will waitlist —
 *  both read off the selection settlement then acts on. Once seating has
 *  settled the card states when, and offers nothing. */
export default function SeatingCard({
  summary,
  discipline,
  timezone,
  busy,
  outcome,
  onSettle,
}: {
  summary: Queue;
  /** The open tab's discipline; null before the band has loaded. */
  discipline: QueueDiscipline | null;
  timezone: string | null;
  busy: boolean;
  /** How many the last settlement moved, stated once it has run. */
  outcome: number | null;
  onSettle: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const settledAt = summary.seating_settled_at;

  return (
    <section className="rail-card">
      <h2>{t("queue.seatingTitle")}</h2>
      <p className="rail-hint">
        {t("queue.deadline", { date: dayIn(summary.seating_deadline, timezone) })}
      </p>
      <p className="rail-hint">
        {settledAt === null
          ? t("queue.notSettled")
          : t("queue.settledOn", { date: dayIn(settledAt, timezone) })}
      </p>
      {discipline !== null && (
        <p className="rail-hint">
          {t("queue.freePlaces", { free: discipline.free, capacity: discipline.capacity })}
        </p>
      )}
      {settledAt === null && (
        <button
          type="button"
          className="btn-danger param-save"
          disabled={busy}
          onClick={() => setConfirming(true)}
        >
          {t("queue.settle")}
        </button>
      )}
      {outcome !== null && <p className="rail-hint">{t("queue.settleDone", { count: outcome })}</p>}

      {confirming && (
        <Modal onClose={() => setConfirming(false)}>
          <div className="modal">
            <h2>{t("queue.settleTitle")}</h2>
            <p>{t("queue.settleBody", { count: summary.pending_demotions })}</p>
            {summary.pending_team_waitlistings > 0 && (
              <p>{t("queue.settleTeams", { count: summary.pending_team_waitlistings })}</p>
            )}
            <p>{t("queue.settleIrreversible")}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={busy}
                onClick={() => {
                  setConfirming(false);
                  onSettle();
                }}
              >
                {t("queue.settleConfirm")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
