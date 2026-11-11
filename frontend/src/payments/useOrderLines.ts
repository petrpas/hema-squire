import { useEffect, useState } from "react";

import { api, type OrderLines } from "../api";

/** What each registration is made of, keyed by registration, loaded with the
 *  Payments phase (design payments-roster-by-order D3).
 *
 *  Its own load beside the two money tables, and independent of them: a
 *  failure here leaves the table readable with its contents unstated, which is
 *  the table's idiom for a cell with nothing to say. Null until it arrives. */
export function useOrderLines(
  slug: string,
  reload: number,
  active: boolean,
): Map<number, OrderLines> | null {
  const [orders, setOrders] = useState<Map<number, OrderLines> | null>(null);

  useEffect(() => {
    if (!active) return;
    api.orderLines(slug).then(
      (rows) => setOrders(new Map(rows.map((order) => [order.registration_id, order]))),
      () => setOrders(new Map()),
    );
  }, [slug, reload, active]);

  return orders;
}
