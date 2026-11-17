import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { FloorLayout } from "../FloorLayout";
import { type FloorSetup, floorApi, type PlanState, planApi } from "../floorApi";
import { AssignmentActions, AssignmentSection, useAssignments } from "./AssignmentSection";
import { PinForm, PinList } from "./PinsSection";
import { PreferencesSection } from "./PreferencesSection";
import { SensitivitySection } from "./SensitivitySection";
import { useVariants, VariantsAsk, VariantsSection } from "./VariantsSection";
import { PublishGate, WorkingDiff } from "./WorkingSection";

/** The Plan tab (spec floor-plan), framed as the office's phases are: in
 *  the work, the working version's difference, the variants each with its
 *  own choice, the referees' seats where they are planned, the pins and the
 *  sensitivity; in the operations panel, the preferences, asking for
 *  variants, the publish gate and re-planning, pinning, and Obsazení's re-run
 *  and prints (spec floor-console, A tab's operations stand in a panel on
 *  the right). */
// a preference left unsaved is not guarded when leaving the tab: it only
// orders the next variants
function ignoreDirty() {}

export default function PlanTab({ slug, onChanged }: { slug: string; onChanged: () => void }) {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<PlanState | null | "error">(null);
  const [setup, setSetup] = useState<FloorSetup | null>(null);
  const assignments = useAssignments(slug);

  const load = useCallback(() => {
    planApi.state(slug).then(setPlan, () => setPlan("error"));
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
  }, [slug]);

  useEffect(load, [load]);

  function changed() {
    load();
    assignments.load();
    onChanged();
  }

  const variants = useVariants(slug, changed);

  if (plan === "error") {
    return (
      <FloorLayout tab="plan">
        <p className="floor-not-yet muted">{t("floor.plan.loadFailed")}</p>
      </FloorLayout>
    );
  }
  if (plan === null || setup === null) {
    return (
      <FloorLayout tab="plan">
        <p>{t("common.loading")}</p>
      </FloorLayout>
    );
  }

  const names = new Map(setup.disciplines.map((d) => [d.id, d.name]));
  const officials = setup.scope.plan_officials && setup.scope.plan_schedule;
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
      <FloorLayout tab="plan" className="floor-plan" rail={preferences}>
        <section className="rail-card">
          <h2>{t("floor.plan.title")}</h2>
          <p>{t("floor.plan.setupMissing")}</p>
        </section>
      </FloorLayout>
    );
  }

  const rail = (
    <>
      <VariantsAsk state={variants} />
      <PublishGate slug={slug} plan={plan} names={names} onChanged={changed} />
      <PinForm slug={slug} setup={setup} onChanged={changed} />
      {officials && (
        <AssignmentActions
          slug={slug}
          setup={setup}
          data={assignments.data}
          load={assignments.load}
        />
      )}
      {preferences}
    </>
  );

  return (
    <FloorLayout tab="plan" className="floor-plan" rail={rail}>
      <WorkingDiff plan={plan} pistes={setup.pistes} />
      <VariantsSection state={variants} names={names} />
      {officials && (
        <AssignmentSection
          slug={slug}
          setup={setup}
          data={assignments.data}
          load={assignments.load}
        />
      )}
      <PinList slug={slug} pins={plan.pins} setup={setup} onChanged={changed} />
      {plan.sensitivity && <SensitivitySection sensitivity={plan.sensitivity} names={names} />}
    </FloorLayout>
  );
}
