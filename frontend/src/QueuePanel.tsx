import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type Queue, api } from "./api";
import QueueEntryLine from "./QueueEntryLine";

/** The organizer's view of where the line falls in every individual
 *  discipline, and the only place `admit_substitute` and its inverse are
 *  reachable from.
 *
 *  Nothing here promotes anyone by a rule: after the seating deadline the
 *  system shows the data and the organizer decides (design Non-Goals), so the
 *  view's job is to make the pending work obvious. A discipline whose queue is
 *  empty is stated as empty rather than hidden. */
export default function QueuePanel({
  slug,
  timezone,
}: {
  slug: string;
  /** The tournament's own zone, the frame each entry's registration moment is
   *  read in; null until the console's tournament detail has arrived. */
  timezone: string | null;
}) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<Queue | null | "error">(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [settled, setSettled] = useState<number | null>(null);

  const refresh = useCallback(() => {
    api.queue(slug).then(setQueue, () => setQueue("error"));
  }, [slug]);

  useEffect(refresh, [refresh]);

  /** Each action reports its own failure rather than a panel-wide banner: the
   *  organizer needs to know which promotion was refused, not that something
   *  was. */
  async function act(run: () => Promise<unknown>) {
    setFailure(null);
    setBusy(true);
    try {
      await run();
      refresh();
    } catch (err) {
      const reason = err instanceof ApiError ? String(err.detail) : String(err);
      setFailure(reason);
    } finally {
      setBusy(false);
    }
  }

  if (queue === null) return <p>{t("common.loading")}</p>;
  if (queue === "error") {
    return (
      <main className="sheet-area">
        <p className="sheet-empty">{t("queue.error")}</p>
      </main>
    );
  }

  const isSettled = queue.seating_settled_at !== null;
  const date = (value: string) => new Date(value).toLocaleDateString("cs");

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("queue.title")}</h1>
        <button
          className="btn-danger"
          onClick={() => setConfirming(true)}
          disabled={isSettled || busy}
        >
          {t("queue.settle")}
        </button>
      </div>

      <div className="sheet-scroll">
        <p className="rail-hint">
          {t("queue.deadline", { date: date(queue.seating_deadline) })} ·{" "}
          {isSettled
            ? t("queue.settledOn", { date: date(queue.seating_settled_at as string) })
            : t("queue.notSettled")}
        </p>
        {settled !== null && (
          <p className="rail-hint">{t("queue.settleDone", { count: settled })}</p>
        )}
        {failure !== null && <p className="field-error">{t("queue.actionFailed", { reason: failure })}</p>}

        {queue.disciplines.length === 0 ? (
          <p className="sheet-empty">{t("queue.noDisciplines")}</p>
        ) : (
          queue.disciplines.map((discipline) => (
            <section key={discipline.slug} className="rail-card">
              <h2>
                {discipline.slug} — {discipline.name}
              </h2>
              <p className="rail-hint">
                {t("queue.freePlaces", {
                  free: discipline.free,
                  capacity: discipline.capacity,
                })}
              </p>

              <h3 className="queue-group">{t("queue.seated")}</h3>
              {discipline.seated.length === 0 ? (
                <p className="muted">{t("queue.noneSeated")}</p>
              ) : (
                <ul className="detail-list">
                  {discipline.seated.map((entry) => (
                    <li key={entry.registration_id}>
                      <div className="detail-row">
                        <span>
                          <QueueEntryLine entry={entry} timezone={timezone} />
                        </span>
                        <button
                          className="link-button"
                          disabled={busy}
                          onClick={() =>
                            void act(() =>
                              api.returnToQueue(slug, entry.registration_id, discipline.slug),
                            )
                          }
                        >
                          {t("queue.returnToQueue")}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              <h3 className="queue-group">{t("queue.queued")}</h3>
              {discipline.queued.length === 0 ? (
                <p className="muted">{t("queue.emptyQueue")}</p>
              ) : (
                <ul className="detail-list">
                  {discipline.queued.map((entry) => (
                    <li key={entry.registration_id}>
                      <div className="detail-row">
                        <span>
                          <QueueEntryLine entry={entry} timezone={timezone} />
                        </span>
                        <button
                          className="link-button"
                          disabled={busy || discipline.free === 0}
                          onClick={() =>
                            void act(() =>
                              api.admitSubstitute(slug, entry.registration_id, discipline.slug),
                            )
                          }
                        >
                          {t("queue.promote")}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))
        )}
      </div>

      {confirming && (
        <div className="modal-backdrop" onClick={() => setConfirming(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{t("queue.settleTitle")}</h2>
            <p>{t("queue.settleBody", { count: queue.pending_demotions })}</p>
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
                  void act(async () => {
                    const result = await api.settleSeating(slug);
                    setSettled(result.demoted);
                  });
                }}
              >
                {t("queue.settleConfirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
