import { useState } from "react";
import { useTranslation } from "react-i18next";

const STAGES = ["pre", "in", "post"] as const;
const PHASES = ["load", "parsing", "matching", "dedup", "payments", "export"] as const;

type Stage = (typeof STAGES)[number];
type Phase = (typeof PHASES)[number];

export default function App() {
  const { t } = useTranslation();
  const [stage, setStage] = useState<Stage>("pre");
  const [phase, setPhase] = useState<Phase>("load");

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">{t("app.title")}</span>
        <nav className="stage-control">
          {STAGES.map((s) => (
            <button
              key={s}
              className={s === stage ? "active" : ""}
              onClick={() => setStage(s)}
            >
              {t(`stage.${s}`)}
            </button>
          ))}
        </nav>
        <span className="tournament-info">{t("tournament.unnamed")}</span>
      </header>

      <nav className="stepper">
        {PHASES.map((p, i) => (
          <button
            key={p}
            className={p === phase ? "active" : ""}
            onClick={() => setPhase(p)}
          >
            <span className="step-number">{i + 1}</span>
            {t(`phase.${p}`)}
          </button>
        ))}
      </nav>

      <div className="workspace">
        <main className="sheet">
          <p className="sheet-empty">{t("sheet.empty")}</p>
        </main>

        <aside className="rail">
          <section>
            <h2>{t("rail.generalRules")}</h2>
          </section>
          <section>
            <h2>{t("rail.columnsForStep")}</h2>
          </section>
          <section>
            <h2>{t("rail.manualEdits")}</h2>
          </section>
        </aside>
      </div>
    </div>
  );
}
