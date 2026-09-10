import { createContext, type KeyboardEvent, type ReactNode, useContext } from "react";
import { useTranslation } from "react-i18next";

/** The payments phase's two tab bands, and the one line of prose beside them.
 *
 *  Two bands rather than one strip of eight tabs. The strip this replaces put
 *  the fencer table beside six queues, and the same fact — this payment belongs
 *  to this fencer — appeared on up to three of them at once, because each queue
 *  asked one of two underlying questions with a filter on it. The questions are
 *  what the bands are: is this the roster or the money, and is the money
 *  credited or not.
 *
 *  The tabs no longer register themselves. Seven independent panels each had to
 *  announce its title and count to a strip that could not know them, with a
 *  registration context and an effect per panel to withdraw a tab whose queue
 *  had gone. With two fixed tables that indirection has nothing left to do: the
 *  console holds the two loads and hands down what it knows.
 *
 *  A count states outstanding work, so the fencer tab carries none: a roster
 *  size sitting among them would read as more of it.
 */

export type PaymentTab = "fencers" | "credited" | "uncredited";

/** Which tab the phase is showing. A context rather than a prop because the
 *  fencer table sits under `SheetArea`, several levels from the band, and only
 *  needs to know whether it is the one being read. */
const OpenTabContext = createContext<PaymentTab | null>(null);

export function PaymentTabsProvider({ open, children }: { open: PaymentTab; children: ReactNode }) {
  return <OpenTabContext.Provider value={open}>{children}</OpenTabContext.Provider>;
}

/** Whether the fencer table is what is being read. True where there is no
 *  provider at all, which is every phase but Payments. */
export function useSheetVisible(): boolean {
  const open = useContext(OpenTabContext);
  return open === null || open === "fencers";
}

interface Entry {
  /** what choosing this tab opens. Null on the payments tab of the first band,
   *  which hands the choice to the caller: it knows which of the two money
   *  tables was last read, and re-opening the one already on screen would
   *  throw that away. */
  opens: PaymentTab | null;
  label: string;
  active: boolean;
  /** undefined where a tab carries no count at all; null while a count is not
   *  yet known — a table states no number rather than a zero it would have to
   *  take back */
  count?: number | null;
  /** the table could not be read, so it has no count to show, and a tab merely
   *  missing its number states nothing */
  failed?: boolean;
  key: string;
}

export default function PaymentTabs({
  open,
  onOpen,
  onOpenPayments,
  creditedCount,
  uncreditedCount,
  creditedFailed = false,
  uncreditedFailed = false,
  note,
}: {
  open: PaymentTab;
  onOpen: (tab: PaymentTab) => void;
  /** Choosing the payments in the first band, which the console resolves to
   *  whichever money table was last read. */
  onOpenPayments: () => void;
  creditedCount: number | null;
  uncreditedCount: number | null;
  creditedFailed?: boolean;
  uncreditedFailed?: boolean;
  /** What the open table has to say that its count cannot. Absent where there
   *  is nothing to say — a line stating a zero is noise about a thing that did
   *  not happen. */
  note?: string | null;
}) {
  const { t } = useTranslation();
  const onPayments = open !== "fencers";

  const bands: Entry[][] = [
    [
      { key: "fencers", opens: "fencers", label: t("payments.tabs.fencers"), active: !onPayments },
      { key: "payments", opens: null, label: t("payments.tabs.payments"), active: onPayments },
    ],
  ];
  // the second band appears only while the money is being read: it answers a
  // question the reader has not asked until then
  if (onPayments) {
    bands.push([
      {
        key: "credited",
        opens: "credited",
        label: t("payments.tabs.credited"),
        active: open === "credited",
        count: creditedCount,
        failed: creditedFailed,
      },
      {
        key: "uncredited",
        opens: "uncredited",
        label: t("payments.tabs.uncredited"),
        active: open === "uncredited",
        count: uncreditedCount,
        failed: uncreditedFailed,
      },
    ]);
  }

  function choose(entry: Entry) {
    if (entry.opens === null) onOpenPayments();
    else onOpen(entry.opens);
  }

  function move(band: Entry[], index: number, event: KeyboardEvent<HTMLButtonElement>) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = band[(index + step + band.length) % band.length];
    if (next) choose(next);
  }

  return (
    <div className="queue-tabs">
      <div className="queue-tab-bands" role="tablist" aria-label={t("payments.tabs.label")}>
        {bands.map((band) => (
          // two boxes, not one box with a gap in it: `stage-control` draws its
          // rule around a whole band, so a margin inside one would leave its
          // top and bottom lines running through the air meant to separate them
          <div className="stage-control" role="presentation" key={band[0]?.key}>
            {band.map((entry, index) => (
              <button
                key={entry.key}
                type="button"
                role="tab"
                id={`payment-tab-${entry.key}`}
                aria-selected={entry.active}
                aria-controls={entry.opens ? `payment-tabpanel-${entry.opens}` : undefined}
                className={entry.active ? "active" : ""}
                onClick={() => choose(entry)}
                onKeyDown={(event) => move(band, index, event)}
              >
                {entry.label}
                {entry.count !== null && entry.count !== undefined && (
                  <span className="tab-count">{entry.count}</span>
                )}
                {entry.failed && (
                  <span className="tab-mark">
                    <span className="visually-hidden">{t("payments.queue.failed")}</span>
                  </span>
                )}
              </button>
            ))}
          </div>
        ))}
      </div>
      {note && <p className="queue-tab-note">{note}</p>}
    </div>
  );
}
