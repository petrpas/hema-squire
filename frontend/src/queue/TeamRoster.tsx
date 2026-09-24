import { IconArrowDown, IconArrowUp } from "@tabler/icons-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import type { QueueTeam } from "../api";
import { registeredMoment } from "../momentText";
import { moneyText } from "./queueColumns";

/** A team discipline's roster in the Queue phase: seated teams above a line at
 *  the discipline's capacity, the waitlist below it in its order, and the two
 *  arrows (spec seating-queue, The team waitlist in the Queue phase).
 *
 *  ↑ admits a waitlisted team while a slot is free; ↓ returns a seated team
 *  while its entering fencer's registration is unpaid. A team is not a row of
 *  the fencer list, so its rows come from their own projection and are drawn
 *  here rather than through the Export grid. */
export default function TeamRoster({
  rows,
  free,
  timezone,
  busy,
  onAdmit,
  onReturn,
}: {
  rows: QueueTeam[];
  free: number;
  timezone: string | null;
  busy: boolean;
  onAdmit: (team: QueueTeam) => void;
  onReturn: (team: QueueTeam) => void;
}) {
  const { t } = useTranslation();
  if (rows.length === 0) return <p className="sheet-empty">{t("queue.noTeams")}</p>;
  const seated = rows.filter((row) => !row.waitlisted).length;

  function standing(row: QueueTeam): string {
    if (!row.waitlisted) return moneyText(t, row, timezone);
    const moment = registeredMoment(row.waitlisted_since, timezone);
    return `${t("queue.position", { position: row.waitlist_position })} ${
      row.demoted ? t("queue.demotedAt", { moment }) : t("queue.enteredAt", { moment })
    }`;
  }

  function arrow(row: QueueTeam) {
    if (row.waitlisted) {
      if (free <= 0) return null;
      return (
        <button
          type="button"
          className="row-action"
          title={t("queue.admitTeamHint")}
          disabled={busy}
          onClick={() => onAdmit(row)}
        >
          <IconArrowUp size={16} stroke={1.5} />
          <span className="visually-hidden">{t("queue.admitTeam")}</span>
        </button>
      );
    }
    if (row.paid) return null;
    return (
      <button
        type="button"
        className="row-action"
        title={t("queue.returnTeamHint")}
        disabled={busy}
        onClick={() => onReturn(row)}
      >
        <IconArrowDown size={16} stroke={1.5} />
        <span className="visually-hidden">{t("queue.returnTeam")}</span>
      </button>
    );
  }

  return (
    <div className="sheet-scroll">
      <table className="sheet-table">
        <thead>
          <tr>
            <th className="col-index">{t("export.column.position")}</th>
            <th>{t("queue.column.team")}</th>
            <th>{t("queue.column.enteredBy")}</th>
            <th className="col-number">{t("queue.column.members")}</th>
            <th>{t("export.column.standing")}</th>
            <th>{t("export.column.action")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <Fragment key={row.team_id}>
              {index === seated && seated > 0 && (
                <tr className="export-line">
                  <td colSpan={6}>{t("queue.teamLine")}</td>
                </tr>
              )}
              <tr>
                <td className="col-index">{index + 1}</td>
                <td>{row.name}</td>
                <td>{row.entering_fencer}</td>
                <td className="col-number">
                  {t("teams.memberCount", {
                    count: row.members,
                    min: row.team_min,
                    max: row.team_max,
                  })}
                </td>
                <td>{standing(row)}</td>
                <td>{arrow(row)}</td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
