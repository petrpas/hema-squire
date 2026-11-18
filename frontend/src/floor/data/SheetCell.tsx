import { useTranslation } from "react-i18next";

import EditableCell from "../../EditableCell";
import type { SheetPerson } from "../floorApi";
import { type SheetField, shown, validCell } from "./columns";

/** One correctable cell of the Data sheet: the office's editable cell, the
 *  hand-corrected ones marked as the office marks a manual edit. Plain text
 *  once the discipline's check-in has closed. */
export default function SheetCell({
  person,
  field,
  heading,
  locked,
  onSave,
}: {
  person: SheetPerson;
  field: SheetField;
  /** The column's heading id, for the cell's accessible name. */
  heading: string;
  locked: boolean;
  onSave: (person: SheetPerson, field: SheetField, raw: string) => void;
}) {
  const { t } = useTranslation();
  const text = shown(person, field);
  const display = person.edited.includes(field) ? (
    <span className="cell-edited">{text}</span>
  ) : (
    text
  );
  // the HR ID leads to the fighter's profile on HEMA Ratings, as on the
  // public roster; beside the editable cell, since a link cannot sit inside
  // the button that opens it
  const profile =
    field === "hr_id" && person.hr_id !== null ? (
      <a
        className="external-link sheet-hr-link"
        href={`https://hemaratings.com/fighters/details/${person.hr_id}/`}
        target="_blank"
        rel="noreferrer"
        aria-label={t("floor.data.hrProfile", { id: person.hr_id })}
      >
        {locked ? display : null}
      </a>
    ) : null;
  if (locked) return profile ?? display;
  const editable = (
    <EditableCell
      label={t(`export.column.${heading}`)}
      display={text === "" && !person.edited.includes(field) ? "—" : display}
      value={person[field]}
      onSave={(raw) => onSave(person, field, raw)}
      validate={(raw) => validCell(field, raw)}
      steady
    />
  );
  if (profile === null) return editable;
  return (
    <span className="sheet-hr">
      {editable}
      {profile}
    </span>
  );
}
