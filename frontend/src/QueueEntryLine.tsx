import { useTranslation } from "react-i18next";

import type { QueueEntry } from "./api";
import { registeredMoment } from "./momentText";

/** One fencer's line in the organizer's queue view: their position, their
 *  name, their club, and the moment they registered.
 *
 *  The moment carries its clock, not its day alone: the queue is ordered by
 *  it, and the line between a seat and a place in the queue can fall between
 *  two fencers who registered the same morning (spec `seating-queue`, Queue
 *  view for the organizer). `timezone` is the tournament's own zone, null
 *  until the tournament detail has arrived. */
export default function QueueEntryLine({
  entry,
  timezone,
}: {
  entry: QueueEntry;
  timezone: string | null;
}) {
  const { t } = useTranslation();
  return (
    <>
      <strong>
        {entry.queue_position !== null &&
          `${t("queue.position", { position: entry.queue_position })} `}
        {entry.fencer}
      </strong>{" "}
      <span className="muted">
        {entry.club && `${entry.club} · `}
        {t("queue.registeredAt", { moment: registeredMoment(entry.registered_at, timezone) })}
      </span>
    </>
  );
}
