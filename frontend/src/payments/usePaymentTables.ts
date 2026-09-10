import { useEffect, useState } from "react";

import { api, type CreditedPayment, type UncreditedPayment } from "../api";

/** One table's load: its rows, whether they are still coming, and whether the
 *  request failed outright. Null rows and `failed` are different answers — a
 *  table that could not be read has no count to state, and a tab merely
 *  missing its number states nothing. */
export interface TableLoad<T> {
  rows: T[] | null;
  failed: boolean;
}

export interface PaymentTables {
  credited: TableLoad<CreditedPayment>;
  uncredited: TableLoad<UncreditedPayment>;
}

/** The payments phase's two loads, held by the console rather than by each
 *  table.
 *
 *  Seven panels used to each own their fetch and announce what they held to a
 *  tab strip that could not know it. With two tables the console can hold both
 *  and hand down what it knows — which is also what lets the line beside the
 *  tab band be computed in one place.
 *
 *  Independent of each other deliberately: one table failing must leave the
 *  other and the fencer table as they were, so the two requests are two states
 *  and never one combined promise.
 *
 *  `reload` is the console's own "the money moved" signal — a landing statement
 *  import, the Fio poll, the lifecycle run, a payment paired or reversed.
 */
export function usePaymentTables(slug: string, reload: number, active: boolean): PaymentTables {
  const [credited, setCredited] = useState<TableLoad<CreditedPayment>>({
    rows: null,
    failed: false,
  });
  const [uncredited, setUncredited] = useState<TableLoad<UncreditedPayment>>({
    rows: null,
    failed: false,
  });

  useEffect(() => {
    if (!active) return;
    api.creditedPayments(slug).then(
      (rows) => setCredited({ rows, failed: false }),
      () => setCredited({ rows: [], failed: true }),
    );
  }, [slug, reload, active]);

  useEffect(() => {
    if (!active) return;
    api.uncreditedPayments(slug).then(
      (rows) => setUncredited({ rows, failed: false }),
      () => setUncredited({ rows: [], failed: true }),
    );
  }, [slug, reload, active]);

  return { credited, uncredited };
}
