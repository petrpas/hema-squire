import { IconChevronDown, IconChevronUp } from "@tabler/icons-react";

import type { SortState } from "./useSort";

/** A column header that sorts its table. The active column states its
 *  direction to assistive technology through `aria-sort` and to the eye
 *  through an outline chevron. */
export default function SortHeader<K extends string>({
  column,
  label,
  sort,
  onSort,
  numeric = false,
}: {
  column: K;
  label: string;
  sort: SortState<K>;
  onSort: (column: K) => void;
  numeric?: boolean;
}) {
  const active = sort.key === column;
  return (
    <th className={numeric ? "col-number" : undefined} aria-sort={active ? sort.direction : "none"}>
      <button type="button" className="sort-header" onClick={() => onSort(column)}>
        {label}
        {active &&
          (sort.direction === "ascending" ? (
            <IconChevronUp size={12} stroke={1.5} aria-hidden />
          ) : (
            <IconChevronDown size={12} stroke={1.5} aria-hidden />
          ))}
      </button>
    </th>
  );
}
