import { useTranslation } from "react-i18next";

import type { DeskPerson } from "../floorApi";

/** One person at the desk: one tick for every discipline and team they are
 *  in, and each entry with its paid mark and its withdrawal. Payment is
 *  shown and decides nothing. */
export function PersonRow({
  person,
  names,
  closed,
  onArrive,
  onWithdraw,
}: {
  person: DeskPerson;
  names: Map<number, string>;
  /** Disciplines whose check-in is closed: their entries no longer change. */
  closed: Set<number>;
  onArrive: (here: boolean) => void;
  onWithdraw: (entry: string, out: boolean) => void;
}) {
  const { t } = useTranslation();
  return (
    <tr className={person.arrived ? "floor-arrived" : ""}>
      <td>
        <input
          type="checkbox"
          aria-label={t("floor.checkin.tick", { name: person.name })}
          checked={person.arrived}
          onChange={(event) => onArrive(event.target.checked)}
        />
      </td>
      <th scope="row">
        {person.name}
        {person.local && <span className="muted"> {t("floor.checkin.local")}</span>}
      </th>
      <td>{person.club}</td>
      <td>
        <ul className="floor-entries">
          {person.entries.map((entry) => (
            <li
              key={`${entry.entry_key}-${entry.discipline_id}`}
              className={entry.withdrawn ? "floor-withdrawn" : ""}
            >
              {names.get(entry.discipline_id)}
              {entry.team !== null && ` (${entry.team})`}
              {entry.paid ? ` · ${t("floor.checkin.paid")}` : ` · ${t("floor.checkin.unpaid")}`}
              {entry.withdrawn && ` · ${t("floor.checkin.withdrawn")}`}{" "}
              {!closed.has(entry.discipline_id) && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => onWithdraw(entry.entry_key, !entry.withdrawn)}
                >
                  {entry.withdrawn ? t("floor.checkin.undoWithdraw") : t("floor.checkin.withdraw")}
                </button>
              )}
            </li>
          ))}
        </ul>
      </td>
    </tr>
  );
}
