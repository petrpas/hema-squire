import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type FloorSetup, floorApi, type SetupSection } from "../floorApi";
import { DaysSection } from "./DaysSection";
import { FormatsSection } from "./FormatsSection";
import { OfficialsSection } from "./OfficialsSection";
import { ParametersSection } from "./ParametersSection";
import { PistesSection } from "./PistesSection";

/** Floor Setup: days, pistes, formats, officials and parameters, each section
 *  with its own save (spec floor-setup). Every parameter is edited here and
 *  nowhere else. */
export default function FloorSetupTab({
  slug,
  onSaved,
  onDirtyChange,
}: {
  slug: string;
  onSaved: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const [setup, setSetup] = useState<FloorSetup | null | "error">(null);
  // a saved section is drawn afresh from the server, dropping its draft
  const [version, setVersion] = useState(0);
  const [dirty, setDirty] = useState<ReadonlySet<SetupSection>>(new Set());

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

  const days = setup.days.days.map((day) => day.date);
  const common = { slug, onSaved: saved, onDirty: report };

  return (
    <div className="setup-panel floor-setup">
      <div className="setup-panel-body">
        <DaysSection key={`days-${version}`} {...common} days={setup.days} />
        <PistesSection key={`pistes-${version}`} {...common} pistes={setup.pistes} days={days} />
        <FormatsSection
          key={`formats-${version}`}
          {...common}
          formats={setup.formats}
          disciplines={setup.disciplines}
        />
        <OfficialsSection
          key={`officials-${version}`}
          {...common}
          officials={setup.officials}
          disciplines={setup.disciplines}
          persons={setup.persons}
          days={days}
        />
        <ParametersSection key={`params-${version}`} {...common} params={setup.params} />
      </div>
    </div>
  );
}
