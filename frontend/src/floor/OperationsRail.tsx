import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { FloorTab } from "./tabs";

/** A floor tab's operations, built as the office console's rail is: the
 *  title "Operace · <tab>", then the cards acting on the tab as a whole or on
 *  its discipline (spec floor-console, A tab's operations stand in a panel on
 *  the right). */
export function OperationsRail({
  tab,
  onClose,
  children,
}: {
  tab: FloorTab;
  /** Given in the narrow drawer, which offers its own close control. */
  onClose?: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const title = `${t("rail.operations")} · ${t(`floor.tabs.${tab}`)}`;
  return (
    <aside className="rail floor-ops" aria-label={title}>
      <div className="floor-ops-title">
        <div className="rail-title">{title}</div>
        {onClose && (
          <button type="button" className="secondary" onClick={onClose}>
            {t("floor.ops.close")}
          </button>
        )}
      </div>
      {children}
    </aside>
  );
}
