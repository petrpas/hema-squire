import { useTranslation } from "react-i18next";

import type { Change, FloorSetup, PlanActivity } from "../floorApi";

const STEP = 5;

function minutes(clock: string): number {
  const [hours = "0", mins = "0"] = clock.split(":");
  return Number(hours) * 60 + Number(mins);
}

/** An activity's short label: discipline, then pool number or round. */
export function activityLabel(activity: PlanActivity, slug: string): string {
  if (activity.kind === "pool") return `${slug} ${activity.ordinal}`;
  if (activity.id.endsWith(":third")) return `${slug} 3.`;
  return activity.final ? `${slug} F` : `${slug} R${activity.round}·${activity.ordinal}`;
}

/** One day as piste × time, five minutes a column, an activity spanning its
 *  columns. Static markup; a change is stated in words beside its outline, so
 *  colour is never the only signal (design add-floor-planner D9). */
export function ScheduleGrid({
  day,
  activities,
  removed,
  changes,
  setup,
  officials,
}: {
  day: string;
  activities: PlanActivity[];
  /** The published version's activities the working one drops. */
  removed: PlanActivity[];
  changes: Change[];
  setup: FloorSetup;
  /** The officials of each activity's block, by activity id. */
  officials?: Map<string, string>;
}) {
  const { t } = useTranslation();
  const today = activities.filter((a) => a.day === day);
  const gone = removed.filter((a) => a.day === day);
  const all = [...today, ...gone];
  if (all.length === 0) return <p className="muted">{t("floor.schedule.empty")}</p>;

  const from = Math.floor(Math.min(...all.map((a) => minutes(a.start))) / 60) * 60;
  const to = Math.ceil(Math.max(...all.map((a) => minutes(a.end))) / 60) * 60;
  const columns = Math.max((to - from) / STEP, 1);
  // the pistes serving one of the day's disciplines, and any an activity
  // stands on; reserve where they serve the day only as reserve
  const held = new Set(setup.days.days.find((d) => d.date === day)?.discipline_ids ?? []);
  const used = new Set(all.map((a) => a.piste_id));
  const reserve = (piste: FloorSetup["pistes"][number]) =>
    !piste.serves.some((s) => held.has(s.discipline_id) && !s.reserve);
  const pistes = setup.pistes
    .filter(
      (piste) =>
        (piste.id !== null && used.has(piste.id)) ||
        piste.serves.some((s) => held.has(s.discipline_id)),
    )
    .sort(
      (a, b) =>
        Number(reserve(a)) - Number(reserve(b)) ||
        setup.pistes.indexOf(a) - setup.pistes.indexOf(b),
    );
  const slugs = new Map(setup.disciplines.map((d) => [d.id, d.slug]));
  const mark = new Map(changes.map((c) => [c.activity, c.kind]));
  const hours: number[] = [];
  for (let h = from; h < to; h += 60) hours.push(h);

  return (
    <div className="floor-grid-band">
      <div
        className="floor-grid"
        style={{ gridTemplateColumns: `5.5rem repeat(${columns}, minmax(0.6rem, 1fr))` }}
      >
        <span className="floor-grid-corner" />
        {hours.map((h) => (
          <span
            key={h}
            className="floor-grid-hour"
            style={{ gridColumn: `${(h - from) / STEP + 2} / span ${60 / STEP}` }}
          >
            {`${String(h / 60).padStart(2, "0")}:00`}
          </span>
        ))}
        {pistes.map((piste, row) => {
          const line = row + 2;
          const here = all.filter((a) => a.piste_id === piste.id);
          return [
            <span key={`p-${piste.id}`} className="floor-grid-piste" style={{ gridRow: line }}>
              {piste.name}
              {reserve(piste) && <span className="muted"> {t("floor.schedule.reserve")}</span>}
            </span>,
            ...here.map((activity) => {
              const kind = gone.includes(activity) ? "removed" : mark.get(activity.id);
              const start = (minutes(activity.start) - from) / STEP + 2;
              const span = Math.max((minutes(activity.end) - minutes(activity.start)) / STEP, 1);
              return (
                <span
                  key={`${kind ?? "a"}-${activity.id}`}
                  className={`floor-grid-activity${kind ? ` floor-grid-${kind}` : ""}`}
                  style={{ gridRow: line, gridColumn: `${start} / span ${span}` }}
                  title={`${activityLabel(activity, slugs.get(activity.discipline_id) ?? "")} ${activity.start}–${activity.end}`}
                >
                  {activityLabel(activity, slugs.get(activity.discipline_id) ?? "")}
                  {officials?.get(activity.id) && (
                    <span className="floor-grid-officials"> · {officials.get(activity.id)}</span>
                  )}
                  {kind && (
                    <span className="floor-grid-mark"> {t(`floor.schedule.change.${kind}`)}</span>
                  )}
                </span>
              );
            }),
          ];
        })}
      </div>
    </div>
  );
}
