import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  api,
  type ExportBandTab,
  type Queue,
  type QueueDiscipline,
  type QueueTeam,
  type SheetRow,
} from "../api";
import { tabCount, tabId, tabLabel } from "../export/tabs";
import { useTabBand } from "../useTabBand";
import QueueRoster from "./QueueRoster";
import SeatingCard from "./SeatingCard";
import TeamRoster from "./TeamRoster";

/** One tab of the band: an individual discipline's roster, drawn from its
 *  export table, or — while the team disciplines feature is on — a team
 *  discipline's waitlist, after them (design team-queue D3). */
type BandTab =
  | { kind: "discipline"; id: string; tab: ExportBandTab }
  | { kind: "team"; id: string; places: QueueDiscipline };

/** The Queue phase: a band of rosters, one per individual discipline and one
 *  per team discipline, with the two arrows that change who holds a seat and
 *  the settle action in the rail (spec seating-queue, Queue view for the
 *  organizer; The team waitlist in the Queue phase).
 *
 *  An individual roster's rows are the discipline's export table and the
 *  summary is `/queue`: deadline, settlement, and every discipline's free
 *  places (design queue-rosters D1). After an action all of it is read again,
 *  and the console is told, since a promotion or a return moves money its
 *  other readers show (D6). */
export default function QueuePhase({
  slug,
  timezone,
  teams,
  revision,
  onChanged,
  renderRail,
}: {
  slug: string;
  timezone: string | null;
  /** Whether the team disciplines feature is on, which offers the team tabs. */
  teams: boolean;
  /** Bumped by the console whenever the tournament changed elsewhere. */
  revision: number;
  onChanged: () => void;
  renderRail: (panel: ReactNode) => ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const [exportTabs, setExportTabs] = useState<ExportBandTab[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [rows, setRows] = useState<SheetRow[]>([]);
  const [teamRows, setTeamRows] = useState<QueueTeam[]>([]);
  const [summary, setSummary] = useState<Queue | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [settled, setSettled] = useState<number | null>(null);

  const band: BandTab[] = [
    ...exportTabs
      .filter((tab) => tab.kind === "discipline")
      .map((tab): BandTab => ({ kind: "discipline", id: tabId(tab), tab })),
    ...(teams ? (summary?.team_disciplines ?? []) : []).map(
      (places): BandTab => ({ kind: "team", id: `team:${places.slug}`, places }),
    ),
  ];
  const open = band.find((candidate) => candidate.id === selected) ?? band[0];
  const bandRef = useTabBand(open?.id ?? "");
  const openSlug =
    open === undefined ? undefined : open.kind === "team" ? open.places.slug : open.tab.key;
  const places =
    open?.kind === "team"
      ? open.places
      : (summary?.disciplines.find((discipline) => discipline.slug === openSlug) ?? null);

  const loadBand = useCallback(() => {
    void api.exportTabs(slug).then(setExportTabs);
    void api.queue(slug).then(setSummary);
  }, [slug]);

  useEffect(loadBand, [loadBand, revision]);

  const openKind = open?.kind;
  const loadRows = useCallback(() => {
    if (openSlug === undefined) return;
    if (openKind === "team") {
      void api.queueTeams(slug, openSlug).then(setTeamRows);
      return;
    }
    void api.exportTable(slug, "discipline", openSlug).then((table) => setRows(table.rows));
  }, [slug, openSlug, openKind]);

  useEffect(loadRows, [loadRows, revision]);

  /** A refusal is stated in words naming why. The arrows are offered only
   *  where the server would act, so one arriving here is a race — another
   *  organizer acting first — and the code it carries is translated rather
   *  than shown (design queue-rosters D2). A refusal that names what it is
   *  about carries its code as its one key. */
  function refusal(err: unknown, action: string): string {
    const detail = err instanceof ApiError ? err.detail : null;
    const code =
      typeof detail === "string"
        ? detail
        : detail !== null && typeof detail === "object"
          ? (Object.keys(detail)[0] ?? null)
          : null;
    const key = code === null ? null : `queue.refused.${code}`;
    return key !== null && i18n.exists(key)
      ? t(key)
      : t("queue.refused.fallback", { action: t(action) });
  }

  async function act(action: string, run: () => Promise<unknown>) {
    setFailure(null);
    setBusy(true);
    try {
      await run();
    } catch (err) {
      setFailure(refusal(err, action));
    } finally {
      setBusy(false);
      loadBand();
      loadRows();
      onChanged();
    }
  }

  const promote = (registrationId: number) => {
    if (openSlug === undefined) return;
    void act("queue.promote", () => api.admitSubstitute(slug, registrationId, openSlug));
  };
  const giveBack = (registrationId: number) => {
    if (openSlug === undefined) return;
    void act("queue.returnToQueue", () => api.returnToQueue(slug, registrationId, openSlug));
  };
  const admitTeam = (team: QueueTeam) =>
    void act("queue.admitTeam", () => api.admitTeam(slug, team.registration_id, team.team_id));
  const returnTeam = (team: QueueTeam) =>
    void act("queue.returnTeam", () =>
      api.returnTeamToWaitlist(slug, team.registration_id, team.team_id),
    );
  const settle = () =>
    void act("queue.settle", async () => {
      const result = await api.settleSeating(slug);
      setSettled(result.demoted);
    });

  function label(candidate: BandTab): string {
    return candidate.kind === "team" ? candidate.places.name : tabLabel(t, candidate.tab);
  }

  function count(candidate: BandTab): string | null {
    if (candidate.kind === "discipline") return tabCount(candidate.tab);
    const { taken, queued } = candidate.places;
    return queued > 0 ? `${taken} + ${queued}` : String(taken);
  }

  return (
    <>
      <main className="sheet-area">
        <div className="sheet-header export-header">
          <h1>{t("queue.title")}</h1>
          <nav className="stage-control stage-control-band" ref={bandRef}>
            {band.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                className={candidate === open ? "active" : ""}
                aria-pressed={candidate === open}
                onClick={() => {
                  setSelected(candidate.id);
                  setFailure(null);
                }}
              >
                {label(candidate)}
                {count(candidate) !== null && <span className="tab-count">{count(candidate)}</span>}
              </button>
            ))}
          </nav>
        </div>
        {failure !== null && <p className="field-error">{failure}</p>}
        {exportTabs.length > 0 && open === undefined ? (
          <p className="sheet-empty">{t("queue.noDisciplines")}</p>
        ) : open?.kind === "team" ? (
          <TeamRoster
            rows={teamRows}
            free={open.places.free}
            timezone={timezone}
            busy={busy}
            onAdmit={admitTeam}
            onReturn={returnTeam}
          />
        ) : open?.kind === "discipline" ? (
          <QueueRoster
            rows={rows}
            slug={open.tab.key}
            capacity={open.tab.capacity}
            freeBySlug={Object.fromEntries(
              (summary?.disciplines ?? []).map((discipline) => [discipline.slug, discipline.free]),
            )}
            timezone={timezone}
            busy={busy}
            onPromote={promote}
            onReturn={giveBack}
          />
        ) : null}
      </main>

      {renderRail(
        summary !== null && (
          <SeatingCard
            summary={summary}
            discipline={places}
            timezone={timezone}
            busy={busy}
            outcome={settled}
            onSettle={settle}
          />
        ),
      )}
    </>
  );
}
