import {
  createContext,
  type KeyboardEvent,
  type ReactNode,
  useCallback,
  useContext,
  useState,
} from "react";
import { useTranslation } from "react-i18next";

/** The payments phase, one table at a time behind a strip of tabs.
 *
 *  Stacked, the queues were four tables piled above the fencer table, each with
 *  its own columns and its own idea of what a row is — a reader had to work out
 *  five times over which table they were in. One at a time is readable; five
 *  are a list of tables.
 *
 *  The fencer list is a tab like the rest, and the first: it is what the phase
 *  is for — who has paid — and the queues are its exceptions.
 *
 *  What the stack did carry, and a naive tab strip would lose, is that work
 *  exists in a queue nobody is looking at. So every queue's tab states its own
 *  count, which is what the headings used to do, and an empty queue keeps its
 *  tab rather than disappearing: the console states an absence instead of
 *  omitting it, and a queue that vanished when emptied would take its zero with
 *  it. The leading tab carries no count — these counts mean outstanding work,
 *  and a roster size sitting among them would read as more of it.
 *
 *  The strip is the console's own tab idiom (`stage-control`), the one the
 *  phase bar and Setup use, so it reads as another set of tabs rather than a
 *  new kind of control.
 */

export interface QueueTabsApi {
  /** A queue announcing itself, how much it holds, and whether it could be
   *  read at all. Called on every change. */
  register: (title: string, count: number | null, failed: boolean) => void;
  /** A queue leaving the phase takes its tab with it. Without this a tab
   *  outlives the queue behind it, and choosing it shows nothing. */
  unregister: (title: string) => void;
  active: string | null;
  /** The leading tab — the fencer table's own. Held here rather than compared
   *  by string at each reader. */
  primary: string;
}

export const QueueTabsContext = createContext<QueueTabsApi | null>(null);

interface Tab {
  title: string;
  count: number | null;
  failed: boolean;
}

const StripContext = createContext<{
  tabs: Tab[];
  choose: (title: string) => void;
} | null>(null);

/** Whether the fencer table is the tab being read. True where there are no tabs
 *  at all, which is every phase but Payments. */
export function useSheetVisible(): boolean {
  const tabs = useContext(QueueTabsContext);
  return tabs === null || tabs.active === tabs.primary;
}

export default function QueueTabs({ primary, children }: { primary: string; children: ReactNode }) {
  // the fencer list leads, and is seeded rather than registered: a queue
  // registers from an effect, and a child's effects run before its parent's, so
  // a tab that registered itself would arrive last however it was written
  const [tabs, setTabs] = useState<Tab[]>([{ title: primary, count: null, failed: false }]);
  const [chosen, setChosen] = useState<string | null>(null);

  const register = useCallback((title: string, count: number | null, failed: boolean) => {
    setTabs((current) => {
      const at = current.findIndex((tab) => tab.title === title);
      if (at === -1) return [...current, { title, count, failed }];
      if (current[at].count === count && current[at].failed === failed) return current;
      const next = [...current];
      next[at] = { title, count, failed };
      return next;
    });
  }, []);

  const unregister = useCallback((title: string) => {
    setTabs((current) => current.filter((tab) => tab.title !== title));
  }, []);

  // the phase opens on the fencer list and stays where it is put. Nothing moves
  // the organizer on its own: a queue that gains work says so on its own tab,
  // which is something to notice rather than something done to them.
  //
  // A choice naming no tab resolves to the list rather than to nothing: the
  // worst failure this can have is a phase that draws neither a table nor a
  // queue, and a queue can stop being drawn
  const active = tabs.some((tab) => tab.title === chosen) ? chosen : primary;

  return (
    <QueueTabsContext.Provider value={{ register, unregister, active, primary }}>
      <StripContext.Provider value={{ tabs, choose: setChosen }}>{children}</StripContext.Provider>
    </QueueTabsContext.Provider>
  );
}

/** The strip itself, drawn where the queues sit — under the sheet's heading and
 *  above whichever table is being read.
 *
 *  Separate from the provider because the two belong at different heights: the
 *  provider has to sit above the fencer table for it to be hideable, and the
 *  strip has to sit below the sheet's own heading.
 */
export function QueueTabStrip() {
  const { t } = useTranslation();
  const strip = useContext(StripContext);
  const tabs = useContext(QueueTabsContext);
  if (strip === null || tabs === null) return null;

  const all = strip.tabs;
  const choose = strip.choose;

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      choose(all[(index + 1) % all.length].title);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      choose(all[(index - 1 + all.length) % all.length].title);
    }
  }

  // two boxes, not one box with a gap in it: `stage-control` draws its rule
  // around the whole strip, so a margin between the first tab and the rest
  // left the top and bottom lines running through the air that was meant to
  // separate them. The groups are `presentation`, so the tabs remain the
  // tablist's own children
  const groups = [all.slice(0, 1), all.slice(1)].filter((group) => group.length > 0);

  return (
    <nav className="queue-tabs" role="tablist" aria-label={t("payments.queue.tabs")}>
      {groups.map((group) => (
        <div className="stage-control" role="presentation" key={group[0].title}>
          {group.map((tab) => {
            const index = all.indexOf(tab);
            return (
              <button
                key={tab.title}
                type="button"
                role="tab"
                id={`queue-tab-${tab.title}`}
                aria-selected={tab.title === tabs.active}
                aria-controls={`queue-tabpanel-${tab.title}`}
                className={tab.title === tabs.active ? "active" : ""}
                onClick={() => choose(tab.title)}
                onKeyDown={(event) => onKeyDown(event, index)}
              >
                {tab.title}
                {tab.count !== null && <span className="tab-count">{tab.count}</span>}
                {/* a queue that could not be read has no count to show, and a tab
              merely missing its number states nothing. The mark is the
              console's own "this one wants attention" (Setup's tabs) */}
                {tab.failed && (
                  <span className="tab-mark">
                    <span className="visually-hidden">{t("payments.queue.failed")}</span>
                  </span>
                )}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
