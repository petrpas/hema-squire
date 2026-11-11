import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { OrderLines } from "../api";
import { orderSummary } from "./orderLines";

/** The Contents cell: what the order holds, and the control that unfolds it
 *  into its lines (spec payments-console, The registration table states what
 *  each order holds / Every order unfolds into its priced lines).
 *
 *  The chevron sits after the summary, as the roster count's does on the
 *  Teams table: the cell is read first and opened second. A row with no lines
 *  — nothing billed, or the lines could not be read — states nothing and
 *  offers nothing to open. */
export default function ContentsCell({
  order,
  open,
  onToggle,
}: {
  order: OrderLines | undefined;
  open: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  const summary = order ? orderSummary(order.lines, t) : null;
  if (!order || order.lines.length === 0) return <span>—</span>;
  const label = open ? t("payments.order.hide") : t("payments.order.show");
  return (
    <>
      <span>{summary ?? "—"}</span>
      <button
        type="button"
        className="roster-toggle"
        aria-expanded={open}
        title={label}
        onClick={onToggle}
      >
        {open ? (
          <IconChevronDown size={14} stroke={1.5} aria-hidden />
        ) : (
          <IconChevronRight size={14} stroke={1.5} aria-hidden />
        )}
        <span className="visually-hidden">{label}</span>
      </button>
    </>
  );
}
