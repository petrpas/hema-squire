import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type FloorSetup, floorApi, type PlanState, planApi } from "../floorApi";
import { AssignmentSection } from "./AssignmentSection";
import { PinsSection } from "./PinsSection";
import { PreferencesSection } from "./PreferencesSection";
import { SensitivitySection } from "./SensitivitySection";
import { VariantsSection } from "./VariantsSection";
import { WorkingSection } from "./WorkingSection";

/** The Plan tab (spec floor-plan): the plan's preferences, variants side by
 *  side, the working version with its difference and the publish gate, the
 *  referees where they are planned, pins, sensitivity. */
// a preference left unsaved is not guarded when leaving the tab: it only
// orders the next variants
function ignoreDirty() {}

export default function PlanTab({ slug, onChanged }: { slug: string; onChanged: () => void }) {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<PlanState | null | "error">(null);
  const [setup, setSetup] = useState<FloorSetup | null>(null);

  const load = useCallback(() => {
    planApi.state(slug).then(setPlan, () => setPlan("error"));
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
  }, [slug]);

  useEffect(load, [load]);

  function changed() {
    load();
    onChanged();
  }

  if (plan === "error") return <p className="floor-not-yet muted">{t("floor.plan.loadFailed")}</p>;
  if (plan === null || setup === null) return <p>{t("common.loading")}</p>;

  const names = new Map(setup.disciplines.map((d) => [d.id, d.name]));
  const preferences = (
    <PreferencesSection
      key={JSON.stringify(setup.preferences)}
      slug={slug}
      onSaved={load}
      onDirty={ignoreDirty}
      preferences={setup.preferences}
    />
  );

  if (plan.setup_missing.length > 0) {
    return (
      <div className="floor-plan">
        <section className="rail-card">
          <h2>{t("floor.plan.title")}</h2>
          <p>{t("floor.plan.setupMissing")}</p>
        </section>
        {preferences}
      </div>
    );
  }

  return (
    <div className="floor-plan">
      {preferences}
      <WorkingSection
        slug={slug}
        plan={plan}
        names={names}
        pistes={setup.pistes}
        onChanged={changed}
      />
      <VariantsSection slug={slug} names={names} onChosen={changed} />
      {setup.scope.plan_officials && setup.scope.plan_schedule && (
        <AssignmentSection slug={slug} setup={setup} />
      )}
      <PinsSection slug={slug} pins={plan.pins} setup={setup} onChanged={changed} />
      {plan.sensitivity && <SensitivitySection sensitivity={plan.sensitivity} names={names} />}
    </div>
  );
}
