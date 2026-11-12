import { IconTrash, IconUserShare } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminTournament, ApiError, api } from "../api";
import AssignOwnerDialog from "./AssignOwnerDialog";
import DeleteTournamentDialog from "./DeleteTournamentDialog";
import SortHeader from "./SortHeader";
import { adminMatches } from "./search";
import { type SortValue, useSort } from "./useSort";

type Column = "name" | "date" | "owner" | "state" | "registrations";

const STATE_ORDER = ["draft", "published", "cancelled"];

function columnValue(tournament: AdminTournament, column: Column): SortValue {
  switch (column) {
    case "name":
      return tournament.display_name;
    case "date":
      return tournament.date;
    case "owner":
      return tournament.owner?.display_name ?? null;
    case "state":
      return STATE_ORDER.indexOf(tournament.state);
    case "registrations":
      return tournament.registration_count;
  }
}

/** Every tournament, drafts and cancelled ones included, searchable and
 *  sortable, each with the admin's owner assignment and delete (spec
 *  user-roles, Admin panel; spec tournament-admin, Tournament ownership
 *  transfer and Tournament deletion and cancellation). An empty tournament
 *  goes at once; one with registrations only through the dialog. */
export default function TournamentsTab({
  tournaments,
  onChanged,
}: {
  tournaments: AdminTournament[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  // by slug, so the dialog states the counts of the list as last loaded — a
  // refusal below refreshes it before the dialog opens
  const [confirmingSlug, setConfirmingSlug] = useState<string | null>(null);
  const confirming = tournaments.find((tournament) => tournament.slug === confirmingSlug);
  const [assigningSlug, setAssigningSlug] = useState<string | null>(null);
  const assigning = tournaments.find((tournament) => tournament.slug === assigningSlug);

  const matching = useMemo(
    () =>
      tournaments.filter((tournament) =>
        adminMatches(
          query,
          [tournament.display_name, tournament.owner?.display_name ?? ""],
          [tournament.slug, tournament.owner?.email ?? null],
        ),
      ),
    [tournaments, query],
  );
  const { sorted, sort, choose } = useSort<AdminTournament, Column>(matching, columnValue, {
    key: "date",
    direction: "descending",
  });

  async function remove(tournament: AdminTournament) {
    if (tournament.registration_count > 0) {
      setConfirmingSlug(tournament.slug);
      return;
    }
    setBusy(tournament.slug);
    try {
      await api.adminDeleteTournament(tournament.slug, false);
      onChanged();
    } catch (error) {
      // a registration arrived after the list was loaded: the server refused,
      // and the delete now needs the confirmation it would have asked for
      if (error instanceof ApiError && error.detail === "has_registrations") {
        onChanged();
        setConfirmingSlug(tournament.slug);
      } else {
        throw error;
      }
    } finally {
      setBusy(null);
    }
  }

  async function confirmDelete(tournament: AdminTournament) {
    await api.adminDeleteTournament(tournament.slug, true);
    setConfirmingSlug(null);
    onChanged();
  }

  const header = (column: Column, label: string, numeric = false) => (
    <SortHeader column={column} label={label} sort={sort} onSort={choose} numeric={numeric} />
  );

  return (
    <section className="rail-card">
      <h2>{t("admin.tournaments.title")}</h2>
      <input
        type="search"
        className="link-filter admin-search"
        value={query}
        placeholder={t("admin.tournaments.search")}
        aria-label={t("admin.tournaments.search")}
        onChange={(event) => setQuery(event.target.value)}
      />
      {sorted.length === 0 ? (
        <p className="rail-hint">
          {tournaments.length === 0 ? t("admin.tournaments.empty") : t("admin.noMatch")}
        </p>
      ) : (
        <table className="sheet-table">
          <thead>
            <tr>
              {header("name", t("admin.tournaments.name"))}
              {header("date", t("admin.tournaments.date"))}
              {header("owner", t("admin.tournaments.owner"))}
              {header("state", t("admin.tournaments.state"))}
              {header("registrations", t("admin.tournaments.registrations"), true)}
              <th className="col-actions col-actions-pair" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((tournament) => (
              <tr key={tournament.slug}>
                <td>
                  {tournament.display_name}
                  <div className="edit-meta">{tournament.slug}</div>
                </td>
                <td>{new Date(tournament.date).toLocaleDateString("cs")}</td>
                <td>{tournament.owner?.display_name ?? "—"}</td>
                <td>{t(`admin.tournaments.states.${tournament.state}`)}</td>
                <td className="col-number">{tournament.registration_count}</td>
                <td className="col-actions col-actions-pair">
                  <button
                    type="button"
                    className="row-action"
                    title={t("admin.tournaments.assignOwner.action")}
                    onClick={() => setAssigningSlug(tournament.slug)}
                  >
                    <IconUserShare size={16} stroke={1.5} />
                  </button>
                  <button
                    type="button"
                    className="row-action"
                    title={t("admin.tournaments.delete.action")}
                    disabled={busy === tournament.slug}
                    onClick={() => void remove(tournament)}
                  >
                    <IconTrash size={16} stroke={1.5} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {assigning && (
        <AssignOwnerDialog
          tournament={assigning}
          onAssigned={() => {
            setAssigningSlug(null);
            onChanged();
          }}
          onClose={() => setAssigningSlug(null)}
        />
      )}
      {confirming && (
        <DeleteTournamentDialog
          tournament={confirming}
          onConfirm={() => confirmDelete(confirming)}
          onClose={() => setConfirmingSlug(null)}
        />
      )}
    </section>
  );
}
