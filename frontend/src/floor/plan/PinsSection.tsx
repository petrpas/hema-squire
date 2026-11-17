import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type FloorSetup, type Pin, planApi } from "../floorApi";

/** Pinned decisions: what each fixes, removable unless a gate added it, and
 *  a form for a discipline's k (spec floor-plan, Decisions are pinned and
 *  unpinned). A discipline's day is Setup's, not a pin. A gate's pin goes by
 *  reopening its gate. */
export function PinsSection({
  slug,
  pins,
  setup,
  onChanged,
}: {
  slug: string;
  pins: Pin[];
  setup: FloorSetup;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [discipline, setDiscipline] = useState(String(setup.disciplines[0]?.id ?? ""));
  const [k, setK] = useState("2");
  const [failed, setFailed] = useState(false);
  const names = new Map(setup.disciplines.map((d) => [String(d.id), d.name]));

  function describe(pin: Pin): string {
    const name = names.get(pin.target) ?? pin.target;
    if (pin.kind === "k") return t("floor.plan.pins.k", { name, k: String(pin.value.k) });
    if (pin.kind === "n") return t("floor.plan.pins.n", { name, n: String(pin.value.n) });
    if (pin.kind === "place") {
      return t("floor.plan.pins.place", {
        activity: pin.target,
        start: String(pin.value.start),
      });
    }
    return t("floor.plan.pins.sequence");
  }

  async function run(action: () => Promise<unknown>) {
    setFailed(false);
    try {
      await action();
      onChanged();
    } catch {
      setFailed(true);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("floor.plan.pins.title")}</h2>
      {pins.length === 0 ? (
        <p className="muted">{t("floor.plan.pins.none")}</p>
      ) : (
        <ul className="floor-pins">
          {pins.map((pin) => (
            <li key={pin.id}>
              {describe(pin)}{" "}
              {pin.gate !== null ? (
                <span className="muted">
                  {t("floor.plan.pins.gate", { gate: t(`floor.tabs.${pin.gate.split(":")[0]}`) })}
                </span>
              ) : (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void run(() => planApi.unpin(slug, pin.id))}
                >
                  {t("floor.setup.remove")}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="floor-row">
        <label>
          {t("floor.plan.pins.discipline")}
          <select value={discipline} onChange={(event) => setDiscipline(event.target.value)}>
            {setup.disciplines.map((d) => (
              <option key={d.id} value={String(d.id)}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("floor.plan.pins.pools")}
          <input
            type="number"
            inputMode="numeric"
            min={1}
            value={k}
            onChange={(event) => setK(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="secondary"
          onClick={() =>
            void run(() =>
              planApi.pin(slug, {
                kind: "k",
                target: discipline,
                value: { k: Number.parseInt(k, 10) },
              }),
            )
          }
        >
          {t("floor.plan.pins.add")}
        </button>
      </div>
      {failed && (
        <p className="save-bar-error" role="alert">
          {t("floor.plan.failed")}
        </p>
      )}
    </section>
  );
}
