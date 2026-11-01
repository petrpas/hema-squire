import { useMemo, useState } from "react";

export type SortDirection = "ascending" | "descending";

export interface SortState<K extends string> {
  key: K;
  direction: SortDirection;
}

/** A column's value for ordering. `null` sorts last in either direction: a row
 *  missing the value is not the smallest of it. */
export type SortValue = string | number | null;

function compare(a: SortValue, b: SortValue): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "cs", { sensitivity: "base" });
}

/** Sort state for one of the admin panel's tables (spec user-roles, Admin
 *  panel): choosing the column already sorted reverses it, choosing another
 *  sorts by it ascending. */
export function useSort<T, K extends string>(
  rows: T[],
  value: (row: T, key: K) => SortValue,
  initial: SortState<K>,
) {
  const [sort, setSort] = useState<SortState<K>>(initial);

  const sorted = useMemo(() => {
    const sign = sort.direction === "ascending" ? 1 : -1;
    return [...rows].sort((left, right) => {
      const a = value(left, sort.key);
      const b = value(right, sort.key);
      if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
      return sign * compare(a, b);
    });
  }, [rows, value, sort]);

  function choose(key: K) {
    setSort((current) =>
      current.key === key
        ? {
            key,
            direction: current.direction === "ascending" ? "descending" : "ascending",
          }
        : { key, direction: "ascending" },
    );
  }

  return { sorted, sort, choose };
}
