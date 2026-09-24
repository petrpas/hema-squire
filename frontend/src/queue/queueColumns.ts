import type { TFunction } from "i18next";

import type { SheetRow } from "../api";
import { CLUB, type ExportColumn, NAME, POSITION, ratingColumn } from "../export/columns";
import { dayIn, registeredMoment } from "../momentText";
import { formatMoney } from "../money";

/** The action column: its cell is the arrow, drawn by the roster, and states
 *  no text of its own. */
export const ACTION: ExportColumn = { id: "action", value: () => "" };

/** Whether this row holds a seat in the discipline, rather than a place in its
 *  queue. The same test `rosterOrder` splits the roster by. */
export const seatedIn = (row: SheetRow, slug: string) => (row.disciplines ?? []).includes(slug);

/** What a seated row's money reads: paid, settled by hand, or what is owed and
 *  by when — the figures settlement decides by (spec seating-queue, Queue view
 *  for the organizer). */
export function moneyText(t: TFunction, row: SheetRow, timezone: string | null): string {
  if (row.registration_id === null) return t("queue.noSeatYet");
  if (row.settled_by_hand) return t("queue.money.waived");
  if (row.paid) return t("queue.money.paid");
  const owed = Number(row.outstanding_amount ?? "0");
  if (!Number.isFinite(owed) || owed <= 0) return t("queue.money.nothingDue");
  const amount = row.outstanding_currency
    ? formatMoney(owed, row.outstanding_currency)
    : String(owed);
  if (row.expires_at === null) return t("queue.money.owes", { amount });
  return t("queue.money.owesBy", { amount, date: dayIn(row.expires_at, timezone) });
}

/** What a queued row reads: its place in the queue and the moment that place
 *  counts from, saying which of the two moments it is — a registration, or a
 *  demotion for non-payment — so a fencer demoted at settlement is legibly
 *  behind one who registered later. */
export function queuedText(
  t: TFunction,
  row: SheetRow,
  slug: string,
  position: number,
  timezone: string | null,
): string {
  const since = row.queued_since?.[slug] ?? row.registered_at;
  const demoted = since !== null && row.registered_at !== null && since !== row.registered_at;
  const moment = registeredMoment(since, timezone);
  const line = `${t("queue.position", { position })} ${
    demoted ? t("queue.demotedAt", { moment }) : t("queue.registeredAt", { moment })
  }`;
  // a registration waiting on its participation condition says what else it
  // waits for, so why it carries no arrow is legible (spec seating-queue)
  const others = (row.conditional ?? []).filter((other) => other !== slug);
  const waitsWhole = others.length > 0 && (row.disciplines ?? []).length === 0;
  const parts = [line];
  if (waitsWhole) parts.push(t("queue.alsoWaitsFor", { disciplines: others.join(", ") }));
  // who has already paid for a place they are waiting for (spec seating-queue)
  if (row.payment_held) parts.push(t("queue.paymentHeld"));
  return parts.join(" · ");
}

/** The Queue roster's columns: who, their rating as Export states it (not
 *  editable here — it is corrected on Export), where they stand, and the arrow.
 *
 *  `seated` is how many rows stand above the line, which is where the queue's
 *  positions start counting. */
export function queueColumns(
  t: TFunction,
  slug: string,
  seated: number,
  timezone: string | null,
): ExportColumn[] {
  return [
    POSITION,
    NAME,
    CLUB,
    { ...ratingColumn(slug), editable: false },
    {
      id: "standing",
      value: (row, index) =>
        seatedIn(row, slug)
          ? moneyText(t, row, timezone)
          : queuedText(t, row, slug, index - seated + 1, timezone),
    },
    ACTION,
  ];
}
