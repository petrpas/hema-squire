import { type ReactNode, useEffect, useRef } from "react";

/** A money table's row, marked and brought into view when a late stamp led
 *  here (design mark-late-payments D6). Scrolled once, when it becomes the
 *  arrived row, and without smooth behaviour: the mark is static, and the
 *  reader's own scrolling afterwards is left alone. */
export default function ArrivedRow({
  arrived,
  children,
}: {
  arrived: boolean;
  children: ReactNode;
}) {
  const ref = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    if (arrived) ref.current?.scrollIntoView?.({ block: "center" });
  }, [arrived]);
  return (
    <tr
      ref={ref}
      className={arrived ? "row-arrived" : undefined}
      aria-current={arrived ? "true" : undefined}
    >
      {children}
    </tr>
  );
}
