import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { DisciplineStrip } from "../DisciplineStrip";
import { FloorLayout } from "../FloorLayout";
import {
  checkinApi,
  type DataSheet,
  type FloorSetup,
  floorApi,
  type SheetMember,
  type SheetPerson,
  sheetApi,
} from "../floorApi";
import AddEntrant from "./AddEntrant";
import AddTeam from "./AddTeam";
import { parsed, type SheetField } from "./columns";
import DataPanel from "./DataPanel";
import SheetTable from "./SheetTable";
import TeamSheetTable from "./TeamSheetTable";

/** Data: the floor's working sheet, one discipline at a time chosen from the
 *  strip (spec floor-data). The office's columns, the day's corrections made
 *  in place while check-in is open, and the snapshot after. */
export default function DataTab({
  slug,
  discipline,
  fallback,
  keptByOrganizer,
}: {
  slug: string;
  discipline?: string;
  /** The discipline kept across the console, for an address naming none. */
  fallback?: string;
  keptByOrganizer: boolean;
}) {
  const { t } = useTranslation();
  const [setup, setSetup] = useState<FloorSetup | null | "draft" | "error">(null);
  const [sheet, setSheet] = useState<DataSheet | null>(null);
  const [failed, setFailed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    floorApi
      .setup(slug)
      .then(setSetup, (error) =>
        setSetup(error instanceof ApiError && error.status === 409 ? "draft" : "error"),
      );
  }, [slug]);

  const disciplines = typeof setup === "object" && setup !== null ? setup.disciplines : [];
  const selected =
    disciplines.find((d) => d.slug === discipline) ??
    disciplines.find((d) => d.slug === fallback) ??
    disciplines[0] ??
    null;
  const selectedId = selected?.id;

  const load = useCallback(() => {
    if (selectedId === undefined) return;
    sheetApi.view(slug, selectedId).then(
      (read) => {
        setSheet(read);
        setFailed(false);
      },
      () => setFailed(true),
    );
  }, [slug, selectedId]);

  useEffect(() => {
    setMessage(null);
    load();
  }, [load]);

  if (setup === "draft" || setup === "error" || selected === null) {
    return (
      <FloorLayout tab="data" className="floor-data">
        <p className={setup === null ? undefined : "muted"}>
          {setup === null
            ? t("common.loading")
            : setup === "draft"
              ? t("floor.data.draft")
              : setup === "error"
                ? t("floor.data.loadFailed")
                : t("floor.data.empty")}
        </p>
      </FloorLayout>
    );
  }

  const shown = sheet !== null && sheet.discipline.id === selected.id ? sheet : null;
  const locked = shown?.closed_at !== null;

  // every write re-reads the sheet: the server orders and marks it
  async function act(write: () => Promise<unknown>): Promise<boolean> {
    try {
      await write();
      load();
      return true;
    } catch {
      load();
      return false;
    }
  }

  function onCell(person: SheetPerson, field: SheetField, raw: string) {
    const subject = field === "rating" || field === "rank" ? person.entry_key : person.person;
    void act(() => sheetApi.cell(slug, subject, field, parsed(field, raw)));
  }

  async function refresh() {
    if (selected === null) return;
    setRefreshing(true);
    setMessage(null);
    try {
      const outcome = await sheetApi.refresh(slug, selected.id);
      setMessage(t("export.ratingsDone", outcome));
      load();
    } catch {
      setMessage(t("export.ratingsFailed"));
    } finally {
      setRefreshing(false);
    }
  }

  function add(name: string, members: SheetMember[]): Promise<boolean> {
    if (shown === null) return Promise.resolve(false);
    // the sheet's own discipline: what the dialog was drawn for
    const id = shown.discipline.id;
    const first = members[0];
    if (shown.discipline.kind === "team") {
      return act(() => sheetApi.addTeam(slug, id, name, members));
    }
    return first === undefined
      ? Promise.resolve(false)
      : act(() => sheetApi.addEntry(slug, id, first));
  }

  const head = (
    <DisciplineStrip slug={slug} tab="data" disciplines={disciplines} current={selected.slug} />
  );

  return (
    <FloorLayout
      tab="data"
      className="floor-data"
      head={head}
      rail={
        <DataPanel
          slug={slug}
          sheet={shown}
          keptByOrganizer={keptByOrganizer}
          refreshing={refreshing}
          message={message}
          onRefresh={() => void refresh()}
          add={
            shown === null || locked ? undefined : shown.discipline.kind === "team" ? (
              <AddTeam sheet={shown} onAdd={add} />
            ) : (
              <AddEntrant sheet={shown} onAdd={add} />
            )
          }
        />
      }
    >
      {!keptByOrganizer && <p className="muted">{t("floor.data.fromRegistrations")}</p>}
      {failed && shown === null ? (
        <p className="muted">{t("floor.data.loadFailed")}</p>
      ) : shown === null ? (
        <p>{t("common.loading")}</p>
      ) : (
        <>
          <h2>
            {shown.discipline.name}{" "}
            <span className="muted">{t("floor.data.count", { count: shown.count })}</span>
          </h2>
          {shown.discipline.kind === "team" ? (
            <TeamSheetTable
              teams={shown.teams}
              locked={locked}
              onCell={onCell}
              onRemove={(team) =>
                void act(() =>
                  team.added
                    ? sheetApi.removeTeam(slug, shown.discipline.id, team.key)
                    : checkinApi.withdraw(slug, team.key),
                )
              }
              onRestore={(team) => void act(() => checkinApi.undoWithdrawal(slug, team.key))}
            />
          ) : (
            <SheetTable
              rows={shown.rows}
              locked={locked}
              onCell={onCell}
              onRemove={(row) =>
                void act(() =>
                  row.added
                    ? sheetApi.removeEntry(slug, shown.discipline.id, row.person)
                    : checkinApi.withdraw(slug, row.entry_key),
                )
              }
              onRestore={(row) => void act(() => checkinApi.undoWithdrawal(slug, row.entry_key))}
            />
          )}
        </>
      )}
    </FloorLayout>
  );
}
