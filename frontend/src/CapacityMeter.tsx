import { useTranslation } from "react-i18next";
import type { OpenDiscipline } from "./api";

/** One discipline's fill on a card (spec design-system, A capacity meter is a
 *  static figure): its name, the figure stated as text, and under them a 4px
 *  track drawing the same ratio. The text is the statement and the track only
 *  draws it, so the track is hidden from assistive technology. Nothing about
 *  it moves — it is drawn at its width and redrawn only by new data. */
export default function CapacityMeter({ discipline }: { discipline: OpenDiscipline }) {
  const { t } = useTranslation();
  const { entered, capacity, queue_length } = discipline;
  const full = capacity > 0 && entered >= capacity;
  const ratio = capacity > 0 ? Math.min(1, entered / capacity) : 0;
  return (
    <li className="meter" data-full={full || undefined}>
      <span className="meter-name">{discipline.name}</span>
      <span className="meter-figure">
        {full
          ? queue_length > 0
            ? t("home.meter.fullWaiting", { count: queue_length })
            : t("home.meter.full")
          : `${entered}/${capacity}`}
      </span>
      <span className="meter-track" aria-hidden="true">
        <span className="meter-fill" style={{ width: `${ratio * 100}%` }} />
      </span>
    </li>
  );
}
