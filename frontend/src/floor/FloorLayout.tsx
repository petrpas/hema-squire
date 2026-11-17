import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import Modal from "../Modal";
import { OperationsRail } from "./OperationsRail";
import type { FloorTab } from "./tabs";
import { useNarrow } from "./useNarrow";

/** One floor tab's frame, the office console's shape: the work, and beside
 *  it the tab's operations panel where the tab has one. Below the canonical
 *  breakpoint the panel is a drawer over the work, opened from "Operace" at
 *  the head of the work (spec floor-console). A tab with nothing to act on
 *  passes no `rail`, and its work takes the full width. */
export function FloorLayout({
  tab,
  head,
  rail,
  className,
  children,
}: {
  tab: FloorTab;
  /** What stands at the head of the work: the discipline strip, a search. */
  head?: ReactNode;
  rail?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const narrow = useNarrow();
  const [drawer, setDrawer] = useState(false);
  const hasRail = rail !== undefined && rail !== null && rail !== false;

  // widening the window puts the panel back beside the work
  useEffect(() => {
    if (!narrow) setDrawer(false);
  }, [narrow]);

  const opener = narrow && hasRail && (
    <button
      type="button"
      className="secondary floor-ops-open"
      aria-haspopup="dialog"
      onClick={() => setDrawer(true)}
    >
      {t("floor.ops.open")}
    </button>
  );

  return (
    <>
      <div className={className ? `floor-work ${className}` : "floor-work"}>
        {(head || opener) && (
          <div className="floor-head">
            <div className="floor-head-main">{head}</div>
            {opener}
          </div>
        )}
        {children}
      </div>
      {hasRail && !narrow && <OperationsRail tab={tab}>{rail}</OperationsRail>}
      {hasRail && narrow && drawer && (
        <Modal placement="drawer" onClose={() => setDrawer(false)}>
          <OperationsRail tab={tab} onClose={() => setDrawer(false)}>
            {rail}
          </OperationsRail>
        </Modal>
      )}
    </>
  );
}
