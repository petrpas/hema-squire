import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import { ITEM_COLUMNS } from "./columns";
import ExportGrid from "./ExportGrid";

/** One extra-item category: the fencers holding a selection in it, what they
 *  chose and how many, and whether they have paid. The paid column is the
 *  registration's — a credit is held against a registration, never against one
 *  of the items it bought. */
export default function ItemsTable({ rows, category }: { rows: SheetRow[]; category: string }) {
  const { t } = useTranslation();
  return <ExportGrid columns={ITEM_COLUMNS(t, category)} rows={rows} />;
}
