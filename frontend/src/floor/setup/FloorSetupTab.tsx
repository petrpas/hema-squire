import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type FloorSetup, floorApi, type SetupSection } from "../floorApi";
import { FormatsTab } from "./FormatsTab";
import { OfficialsTab } from "./OfficialsTab";
import { ParamsTab } from "./ParamsTab";
import { PistesTab } from "./PistesTab";
import { ScheduleTab } from "./ScheduleTab";
import { ScopeTab } from "./ScopeTab";
import { SETUP_TABS, type SetupTab, SetupTabs } from "./SetupTabs";

/** The section each Setup tab saves. */
const SECTION_OF: Record<SetupTab, SetupSection> = {
  scope: "scope",
  schedule: "days",
  formats: "formats",
  officials: "officials",
  pistes: "pistes",
  params: "params",
};

/** Which tab a waiting condition of the summary is resolved on. */
function tabOf(code: string): SetupTab | null {
  const kind = code.split(":")[0];
  if (kind === "days" || kind === "day") return "schedule";
  if (kind === "piste") return "pistes";
  if (kind === "format" || kind === "take_over") return "formats";
  return null;
}

/** Floor Setup: small tabs across the top, each with its own save (spec
 *  floor-setup, Floor Setup has its own tabs). Every tab stays mounted and
 *  the others are hidden, so a draft survives switching between them; what
 *  scope does not plan is not offered. */
export default function FloorSetupTab({
  slug,
  missing,
  onSaved,
  onDirtyChange,
}: {
  slug: string;
  /** Setup's waiting conditions, from the console's summary. */
  missing: string[];
  onSaved: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const [setup, setSetup] = useState<FloorSetup | null | "error">(null);
  // a saved section is drawn afresh from the server, dropping its draft
  const [version, setVersion] = useState(0);
  const [dirty, setDirty] = useState<ReadonlySet<SetupSection>>(new Set());
  const [chosen, setChosen] = useState<SetupTab | null>(null);

  const load = useCallback(() => {
    floorApi.setup(slug).then(
      (loaded) => {
        setSetup(loaded);
        setVersion((v) => v + 1);
      },
      () => setSetup("error"),
    );
  }, [slug]);

  useEffect(load, [load]);

  useEffect(() => onDirtyChange(dirty.size > 0), [dirty, onDirtyChange]);

  const report = useCallback((section: SetupSection, isDirty: boolean) => {
    setDirty((current) => {
      if (current.has(section) === isDirty) return current;
      const next = new Set(current);
      if (isDirty) next.add(section);
      else next.delete(section);
      return next;
    });
  }, []);

  function saved() {
    load();
    onSaved();
  }

  if (setup === "error") return <p className="muted">{t("floor.setup.loadFailed")}</p>;
  if (setup === null) return <p>{t("common.loading")}</p>;

  const { scope } = setup;
  const tabs = SETUP_TABS.filter((tab) => {
    if (tab === "schedule" || tab === "pistes" || tab === "params") return scope.plan_schedule;
    if (tab === "officials") return scope.plan_schedule && scope.plan_officials;
    return true;
  });
  const incomplete = new Set(
    missing.map(tabOf).filter((tab): tab is SetupTab => tab !== null && tabs.includes(tab)),
  );
  const dirtyTabs = new Set(tabs.filter((tab) => dirty.has(SECTION_OF[tab])));
  // where nothing was chosen yet: the first tab holding something incomplete
  const tab =
    chosen !== null && tabs.includes(chosen)
      ? chosen
      : (tabs.find((candidate) => incomplete.has(candidate)) ?? "scope");

  const days = setup.days.days.map((day) => day.date);
  const common = { slug, onSaved: saved, onDirty: report };

  function panel(id: SetupTab, content: ReactNode) {
    if (!tabs.includes(id)) return null;
    return (
      <div
        role="tabpanel"
        id={`floor-setup-panel-${id}`}
        aria-labelledby={`floor-setup-tab-${id}`}
        hidden={tab !== id}
      >
        {content}
      </div>
    );
  }

  return (
    <div className="setup-panel floor-setup">
      <div className="setup-panel-header floor-setup-header">
        <SetupTabs
          tabs={tabs}
          tab={tab}
          incomplete={incomplete}
          dirty={dirtyTabs}
          onSelect={setChosen}
        />
      </div>
      <div className="setup-panel-body">
        {panel("scope", <ScopeTab key={`scope-${version}`} {...common} scope={scope} />)}
        {panel(
          "schedule",
          <ScheduleTab
            key={`days-${version}`}
            {...common}
            days={setup.days}
            disciplines={setup.disciplines}
            multiDay={scope.multi_day}
          />,
        )}
        {panel(
          "formats",
          <FormatsTab
            key={`formats-${version}`}
            {...common}
            formats={setup.formats}
            disciplines={setup.disciplines}
            scope={scope}
          />,
        )}
        {panel(
          "officials",
          <OfficialsTab
            key={`officials-${version}`}
            {...common}
            officials={setup.officials}
            disciplines={setup.disciplines}
            persons={setup.persons}
            days={scope.multi_day ? days : []}
          />,
        )}
        {panel(
          "pistes",
          <PistesTab
            key={`pistes-${version}`}
            {...common}
            pistes={setup.pistes}
            disciplines={setup.disciplines}
          />,
        )}
        {panel("params", <ParamsTab key={`params-${version}`} {...common} params={setup.params} />)}
      </div>
    </div>
  );
}
