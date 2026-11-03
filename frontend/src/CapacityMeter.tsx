import { useTranslation } from "react-i18next";
import type { OpenDiscipline } from "./api";

/** What a meter draws: a discipline's figures, or an event's program item
 *  with no queue (spec fencer-home, An event's card meters its program). */
export type Meter = Pick<OpenDiscipline, "name" | "entered" | "capacity" | "queue_length">;

/** One discipline's or program item's fill on a card (spec design-system, A capacity meter is a
 *  static figure): its name, the figure stated as text, and under them a 4px
 *  track drawing the same ratio. The text is the statement and the track only
 *  draws it, so the track is hidden from assistive technology. Nothing about
 *  it moves — it is drawn at its width and redrawn only by new data. */
export default function CapacityMeter({ meter }: { meter: Meter }) {
  const { t } = useTranslation();
  const { entered, capacity, queue_length } = meter;
  const full = capacity > 0 && entered >= capacity;
  return (
    <li className="meter" data-full={full || undefined}>
      <span className="meter-name">{meter.name}</span>
      <span className="meter-figure">
        {full
          ? queue_length > 0
            ? t("home.meter.fullWaiting", { count: queue_length })
            : t("home.meter.full")
          : `${entered}/${capacity}`}
      </span>
      <MeterTrack entered={entered} capacity={capacity} />
    </li>
  );
}

/** The track alone: 4px, the measured ratio filled, hidden from assistive
 *  technology because the text beside it is the statement. Full fills in
 *  `--stamp` through the `data-full` its container carries. */
export function MeterTrack({ entered, capacity }: { entered: number; capacity: number }) {
  const ratio = capacity > 0 ? Math.min(1, entered / capacity) : 0;
  return (
    <span className="meter-track" aria-hidden="true">
      <span className="meter-fill" style={{ width: `${ratio * 100}%` }} />
    </span>
  );
}
