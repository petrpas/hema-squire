import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import * as routes from "../../routes";
import { type BracketView, bracketApi, type FloorSetup, floorApi } from "../floorApi";
import { openPdf } from "../pdf";
import { usePolled } from "../usePolled";
import { BracketBoutRow } from "./BracketBoutRow";

/** Pavouk: the proposed bracket and "Potvrdit postup", then its rounds with
 *  every bout recorded and corrected, the third place, and printing (spec
 *  floor-bracket). */
export default function BracketTab({ slug, discipline }: { slug: string; discipline?: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [setup, setSetup] = useState<FloorSetup | null>(null);

  useEffect(() => {
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
  }, [slug]);

  const selected =
    setup?.disciplines.find((d) => d.slug === discipline) ?? setup?.disciplines[0] ?? null;
  const fetchView = useCallback(
    (): Promise<BracketView | null> =>
      selected === null ? Promise.resolve(null) : bracketApi.view(slug, selected.id),
    [slug, selected],
  );
  const { data, failed, reload } = usePolled(fetchView, selected?.id);

  if (setup === null || selected === null) return <p>{t("common.loading")}</p>;
  const name = (key: string) => data?.names[key] ?? key;

  function roundLabel(round: number, position: number, rounds: number): string {
    if (round === rounds - 1)
      return position === 1 ? t("floor.bracket.third") : t("floor.bracket.final");
    if (round === rounds - 2) return t("floor.bracket.semifinal", { n: position + 1 });
    return t("floor.bracket.round", { size: 2 ** (rounds - round), n: position + 1 });
  }

  return (
    <div className="floor-data floor-bracket">
      <label className="floor-search">
        {t("floor.pools.discipline")}
        <select
          value={selected.slug}
          onChange={(event) => navigate(routes.floorPath(slug, "bracket", event.target.value))}
        >
          {setup.disciplines.map((d) => (
            <option key={d.id} value={d.slug}>
              {d.name}
            </option>
          ))}
        </select>
      </label>

      {data === null ? (
        <p className="muted">{failed ? t("floor.pools.failed") : t("common.loading")}</p>
      ) : data.bracket === null ? (
        !data.pools_closed ? (
          (() => {
            // a discipline that takes over waits on its source's pools
            const source = setup.disciplines.find((d) => d.id === data.source) ?? selected;
            return (
              <p>
                {source === selected
                  ? t("floor.bracket.poolsOpen")
                  : t("floor.bracket.sourceOpen", { name: source.name })}{" "}
                <Link to={routes.floorPath(slug, "pools", source.slug)}>
                  {t("floor.tabs.pools")}
                </Link>
              </p>
            );
          })()
        ) : data.proposal === null ? (
          <p className="muted">{t("floor.bracket.none")}</p>
        ) : (
          <section className="rail-card">
            <h2>
              {t("floor.bracket.proposal", {
                size: data.proposal.size,
                advancing: data.proposal.advancing,
              })}
            </h2>
            <ol className="floor-proposal">
              {data.proposal.slots.map((slot) => (
                <li key={slot.position}>
                  {slot.seed === null ? (
                    <span className="muted">{t("floor.bracket.bye")}</span>
                  ) : (
                    `${slot.seed}. ${slot.key ? name(slot.key) : ""}`
                  )}
                </li>
              ))}
            </ol>
            {(data.proposal.unplaced ?? []).length > 0 && (
              <p className="floor-missing">
                {t("floor.bracket.unplaced", {
                  names: (data.proposal.unplaced ?? []).map(name).join(", "),
                })}
              </p>
            )}
            <button
              type="button"
              className="btn-primary"
              onClick={() => void bracketApi.confirm(slug, selected.id).then(reload)}
            >
              {t("floor.bracket.confirm")}
            </button>
          </section>
        )
      ) : (
        (() => {
          const bracket = data.bracket;
          const rounds = Math.log2(bracket.size);
          const byRound = new Map<number, typeof bracket.bouts>();
          for (const bout of bracket.bouts) {
            byRound.set(bout.round, [...(byRound.get(bout.round) ?? []), bout]);
          }
          return (
            <section className="rail-card">
              <h2>
                {t(`floor.bracket.state.${data.state}`)}{" "}
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void openPdf(bracketApi.sheetUrl(slug, selected.id))}
                >
                  {t("floor.bracket.print")}
                </button>
              </h2>
              {[...byRound.entries()]
                .sort(([x], [y]) => x - y)
                .map(([round, bouts]) => (
                  <ul key={round} className="floor-bracket-round">
                    {bouts.map((bout) => (
                      <BracketBoutRow
                        key={`${bout.id}-${bout.version}`}
                        slug={slug}
                        discipline={selected.id}
                        bout={bout}
                        name={name}
                        label={roundLabel(bout.round, bout.position, rounds)}
                        onChanged={reload}
                      />
                    ))}
                  </ul>
                ))}
              {data.state === "seeded" && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void bracketApi.reopen(slug, selected.id).then(reload)}
                >
                  {t("floor.bracket.reopen")}
                </button>
              )}
            </section>
          );
        })()
      )}
    </div>
  );
}
