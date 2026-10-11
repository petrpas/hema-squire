import { useTranslation } from "react-i18next";

/** What a roster's Paid cell says: yes or no where the server stated one,
 *  and nothing where it claims nothing — a queued row, or an entrant the
 *  organizer has not ticked on a tournament Squire does not collect for. */
export function PaidCell({ paid }: { paid: "yes" | "no" | null }) {
  const { t } = useTranslation();
  return <td>{paid === null ? null : t(`export.${paid}`)}</td>;
}

/** The capacity line, a row of the table with a rule above it, as the Export
 *  tab draws it. Its label names a queue only where one stands below it. */
export function CapacityLine({ columns, queued }: { columns: number; queued: boolean }) {
  const { t } = useTranslation();
  return (
    <tr className="export-line">
      <td colSpan={columns}>{t(queued ? "export.line.queue" : "export.line.capacity")}</td>
    </tr>
  );
}

/** A HEMA Ratings identifier, leading to the fighter's profile there. */
export function HrIdCell({ hrId }: { hrId: number | null }) {
  return (
    <td className="col-number">
      {hrId !== null && (
        <a
          className="external-link"
          href={`https://hemaratings.com/fighters/details/${hrId}/`}
          target="_blank"
          rel="noreferrer"
        >
          {hrId}
        </a>
      )}
    </td>
  );
}
