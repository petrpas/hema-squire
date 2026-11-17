import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import type { FloorDiscipline, Serves } from "../floorApi";

type Tier = "no" | "regular" | "reserve";

/** Which disciplines a piste or an official serves, each "ne", "běžně" or
 *  "rezerva" (spec floor-setup, Pistes and their availability, Officials and
 *  their availability). The choice is its tab's draft: closing saves
 *  nothing. */
export function ServesDialog({
  title,
  note,
  serves,
  disciplines,
  onChange,
  onClose,
}: {
  title: string;
  /** what a reserve means for what is being edited */
  note: string;
  serves: Serves[];
  disciplines: FloorDiscipline[];
  onChange: (serves: Serves[]) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();

  function tierOf(discipline: number): Tier {
    const found = serves.find((s) => s.discipline_id === discipline);
    if (found === undefined) return "no";
    return found.reserve ? "reserve" : "regular";
  }

  function choose(discipline: number, tier: Tier) {
    const rest = serves.filter((s) => s.discipline_id !== discipline);
    const next =
      tier === "no" ? rest : [...rest, { discipline_id: discipline, reserve: tier === "reserve" }];
    // kept in discipline order, as the server lists them
    const order = disciplines.map((d) => d.id);
    onChange(next.sort((a, b) => order.indexOf(a.discipline_id) - order.indexOf(b.discipline_id)));
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal floor-serves-dialog">
        <h2>{title}</h2>
        <table className="sheet-table">
          <thead>
            <tr>
              <th scope="col">{t("floor.setup.serves.discipline")}</th>
              {(["no", "regular", "reserve"] as const).map((tier) => (
                <th key={tier} scope="col">
                  {t(`floor.setup.serves.${tier}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {disciplines.map((discipline) => (
              <tr key={discipline.id}>
                <th scope="row">{discipline.name}</th>
                {(["no", "regular", "reserve"] as const).map((tier) => (
                  <td key={tier}>
                    <input
                      type="radio"
                      name={`serves-${discipline.id}`}
                      aria-label={`${discipline.name}: ${t(`floor.setup.serves.${tier}`)}`}
                      checked={tierOf(discipline.id) === tier}
                      onChange={() => choose(discipline.id, tier)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted floor-serves-note">{note}</p>
        <div className="modal-actions floor-day-actions">
          <button type="button" className="btn-primary" onClick={onClose}>
            {t("floor.setup.done")}
          </button>
        </div>
      </div>
    </Modal>
  );
}

/** What a serves list reads as on its row: "Longsword, Sabre (rezerva)". */
export function servesText(
  serves: Serves[],
  disciplines: FloorDiscipline[],
  reserveWord: string,
  none: string,
): string {
  const named = serves
    .map((s) => {
      const discipline = disciplines.find((d) => d.id === s.discipline_id);
      if (discipline === undefined) return null;
      return s.reserve ? `${discipline.name} (${reserveWord})` : discipline.name;
    })
    .filter((name): name is string => name !== null);
  return named.join(", ") || none;
}
