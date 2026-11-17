import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { FloorLayout } from "../FloorLayout";
import {
  type Assignments,
  type FloorSetup,
  floorApi,
  officialsApi,
  type PlanState,
  planApi,
} from "../floorApi";
import { ScheduleGrid } from "./ScheduleGrid";

/** Rozvrh, a tab of its own at the full width with no operations panel
 *  (spec floor-plan, Rozvrh draws piste × time): the published version where
 *  there is one, the working version where it is asked for or alone, with
 *  its changes marked against the published one. Read on every open, so what
 *  Plán chose or published is what it draws. */
export default function ScheduleTab({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation();
  const [plan, setPlan] = useState<PlanState | null>(null);
  const [setup, setSetup] = useState<FloorSetup | null>(null);
  const [showWorking, setShowWorking] = useState(false);
  const [day, setDay] = useState<string | null>(null);
  const [assigned, setAssigned] = useState<Assignments | null>(null);

  useEffect(() => {
    planApi.state(slug).then(setPlan, () => setPlan(null));
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
    officialsApi.view(slug).then(setAssigned, () => setAssigned(null));
  }, [slug]);

  const both = plan?.working != null && plan.published != null;
  const shown =
    plan === null ? null : showWorking || !plan.published ? plan.working : plan.published;
  const days = [...new Set((shown?.activities ?? []).map((a) => a.day))].sort();
  const chosenDay = day !== null && days.includes(day) ? day : (days[0] ?? null);

  return (
    <FloorLayout tab="schedule" className="floor-schedule">
      <h2>{t("floor.schedule.title")}</h2>
      {shown === null || setup === null ? (
        <p className="muted">{t("floor.schedule.none")}</p>
      ) : (
        <>
          {both && (
            <fieldset className="floor-choice">
              <legend className="visually-hidden">{t("floor.schedule.version")}</legend>
              <button
                type="button"
                className={showWorking ? "secondary" : "secondary active"}
                aria-pressed={!showWorking}
                onClick={() => setShowWorking(false)}
              >
                {t("floor.schedule.published")}
              </button>
              <button
                type="button"
                className={showWorking ? "secondary active" : "secondary"}
                aria-pressed={showWorking}
                onClick={() => setShowWorking(true)}
              >
                {t("floor.schedule.working")}
              </button>
            </fieldset>
          )}
          {days.length > 1 && (
            <fieldset className="floor-choice">
              <legend className="visually-hidden">{t("floor.schedule.day")}</legend>
              {days.map((d) => (
                <button
                  key={d}
                  type="button"
                  className={d === chosenDay ? "secondary active" : "secondary"}
                  aria-pressed={d === chosenDay}
                  onClick={() => setDay(d)}
                >
                  {new Date(`${d}T12:00:00`).toLocaleDateString(i18n.language, {
                    weekday: "short",
                    day: "numeric",
                    month: "numeric",
                  })}
                </button>
              ))}
            </fieldset>
          )}
          {chosenDay !== null && (
            <ScheduleGrid
              day={chosenDay}
              activities={shown.activities}
              removed={
                showWorking && both
                  ? (plan?.published?.activities ?? []).filter((a) =>
                      plan?.diff.some((c) => c.activity === a.id && c.kind === "removed"),
                    )
                  : []
              }
              changes={showWorking && both ? (plan?.diff ?? []) : []}
              setup={setup}
              officials={officialNames(assigned, showWorking && both)}
            />
          )}
        </>
      )}
    </FloorLayout>
  );
}

/** Each published activity's officials, by the block that holds it. A
 *  working version's blocks have none yet. */
function officialNames(assigned: Assignments | null, working: boolean): Map<string, string> {
  const out = new Map<string, string>();
  if (assigned === null || working) return out;
  for (const block of assigned.blocks) {
    const names = block.seats.flatMap((s) => (s.name ? [s.name] : [])).join(", ");
    for (const activity of block.activities) out.set(activity, names);
  }
  return out;
}
