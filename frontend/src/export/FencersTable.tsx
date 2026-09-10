import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import { FENCERS_COLUMNS } from "./columns";
import ExportGrid from "./ExportGrid";

/** The fencer table as the Export phase states it: every fencer the tournament
 *  knows, in registration order, with their disciplines and their paid mark. */
export default function FencersTable({ rows }: { rows: SheetRow[] }) {
  const { t } = useTranslation();
  return <ExportGrid columns={FENCERS_COLUMNS(t)} rows={rows} />;
}
