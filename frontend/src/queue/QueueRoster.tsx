import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import ExportGrid from "../export/ExportGrid";
import { rosterOrder } from "../export/ordering";
import ArrowCell from "./ArrowCell";
import { queueColumns } from "./queueColumns";

/** One discipline's roster as the Queue phase draws it: the same rows, in the
 *  same order and with the same line as the Export roster in its own order —
 *  by construction, since both are `rosterOrder` over the discipline's export
 *  table (spec seating-queue, Queue view for the organizer). No seeding order
 *  and no active-only switch: the unpaid are what this phase is about. */
export default function QueueRoster({
  rows,
  slug,
  capacity,
  free,
  timezone,
  busy,
  onPromote,
  onReturn,
}: {
  rows: SheetRow[];
  slug: string;
  capacity: number | null;
  free: number;
  timezone: string | null;
  busy: boolean;
  onPromote: (registrationId: number) => void;
  onReturn: (registrationId: number) => void;
}) {
  const { t } = useTranslation();
  const { rows: ordered, line } = rosterOrder(rows, slug, capacity, "queue", false);
  const seated = line.after ?? ordered.length;
  const columns = queueColumns(t, slug, seated, timezone);

  return (
    <ExportGrid
      columns={columns}
      rows={ordered}
      line={line}
      cell={(row, column) =>
        column.id === "action" ? (
          <ArrowCell
            row={row}
            slug={slug}
            free={free}
            busy={busy}
            onPromote={onPromote}
            onReturn={onReturn}
          />
        ) : null
      }
    />
  );
}
