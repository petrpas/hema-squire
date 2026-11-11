import { useTranslation } from "react-i18next";

/** What a roster's Paid cell says: yes or no where the server stated one,
 *  and nothing where it claims nothing — a queued row, or an entrant the
 *  organizer has not ticked on a tournament Squire does not collect for. */
export function PaidCell({ paid }: { paid: "yes" | "no" | null }) {
  const { t } = useTranslation();
  return <td className="col-paid">{paid === null ? null : t(`export.${paid}`)}</td>;
}

/** A header in two lengths: the whole word, and the short one a phone shows
 *  in its place (spec public-entrants, A roster fits a phone). */
export function TwoLengthHeader({
  wide,
  narrow,
  className,
}: {
  wide: string;
  narrow: string;
  className: string;
}) {
  return (
    <th className={className}>
      <span className="label-wide">{wide}</span>
      <span className="label-narrow">{narrow}</span>
    </th>
  );
}

/** The capacity line, a row of the table with a rule above it, as the Export
 *  tab draws it. Its label names a queue only where one stands below it. A
 *  side event's line states its capacity instead: no queue ever stands below
 *  it, so the line marks the limit and not where the places ran out. */
export function CapacityLine({
  columns,
  queued,
  capacity = null,
}: {
  columns: number;
  queued: boolean;
  capacity?: number | null;
}) {
  const { t } = useTranslation();
  const label =
    capacity !== null
      ? t("export.line.limit", { capacity })
      : t(queued ? "export.line.queue" : "export.line.capacity");
  return (
    <tr className="export-line">
      <td colSpan={columns}>{label}</td>
    </tr>
  );
}

/** A HEMA Ratings identifier, leading to the fighter's profile there. A
 *  phone shows the arrow alone; the identifier stays the link's name, so a
 *  screen reader states it either way (spec public-entrants, A roster fits a
 *  phone). */
export function HrIdCell({ hrId }: { hrId: number | null }) {
  return (
    <td className="col-number col-hr">
      {hrId !== null && (
        <a
          className="external-link"
          href={`https://hemaratings.com/fighters/details/${hrId}/`}
          target="_blank"
          rel="noreferrer"
          aria-label={`HR ${hrId}`}
        >
          <span className="hr-number">{hrId}</span>
        </a>
      )}
    </td>
  );
}
