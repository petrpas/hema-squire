// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DedupPanel from "./dedup/DedupPanel";
import ImportPanel from "./ImportPanel";
import MatchPanel from "./MatchPanel";
import OperationsIndicator from "./OperationsIndicator";
import { type Operation, type OperationsReport, api } from "./api";
import i18n from "./i18n";
import useOperations, { type OperationsView } from "./useOperations";

// Long console work is reported from the tournament's record, not from what a
// component happens to have done (spec `console-operations`).

const t = i18n.getFixedT("cs");

// React only treats updates as batched test work when it is told it is under
// test; without this every act() call warns.
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function text() {
  return host?.textContent ?? "";
}

function buttons() {
  return [...(host?.querySelectorAll("button") ?? [])] as HTMLButtonElement[];
}

function labelled(label: string) {
  return buttons().find((button) => button.textContent?.includes(label));
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function operation(over: Partial<Operation> = {}): Operation {
  return {
    id: 1,
    kind: "parse",
    status: "running",
    total: 220,
    done: 60,
    started_at: "2026-04-01T14:32:00Z",
    finished_at: null,
    outcome: {},
    ...over,
  };
}

function view(over: Partial<OperationsView> = {}): OperationsView {
  return { running: null, concluded: {}, refresh: () => {}, ...over };
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "importStatus").mockResolvedValue({
    batch: null,
    total: { rows: 0, files: 0 },
  });
  vi.spyOn(api, "hrStatus").mockResolvedValue({ fighters: 12, last_refresh: null });
  vi.spyOn(api, "dedupGroups").mockResolvedValue([]);
});

afterEach(() => {
  host?.remove();
  host = null;
  vi.useRealTimers();
});

describe("the standing indicator", () => {
  it("states the count while work runs", () => {
    mount(<OperationsIndicator running={operation()} />);

    expect(text()).toContain(t("operation.label.parse"));
    expect(text()).toContain(t("operation.progress", { count: 220, done: 60 }));
  });

  it("counts an import in rows and a matching in questions", () => {
    mount(<OperationsIndicator running={operation({ kind: "match", total: 4, done: 1 })} />);

    expect(text()).toContain(t("operation.questions", { count: 4, done: 1 }));
  });

  it("shows nothing at all when nothing runs", () => {
    mount(<OperationsIndicator running={null} />);

    expect(text()).toBe("");
  });

  it("states the conclusion and then leaves", async () => {
    vi.useFakeTimers();
    const card = document.createElement("div");
    host = card;
    document.body.append(card);
    const root = createRoot(card);
    act(() => root.render(<OperationsIndicator running={operation()} />));

    act(() => root.render(<OperationsIndicator running={null} />));
    expect(text()).toContain(t("operation.done"));
    expect(card.querySelector(".operation-indicator")?.className).toContain("leaving");

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    expect(text()).toBe("");
  });
});

describe("a phase panel", () => {
  it("disables its action and names the work while another phase runs", async () => {
    mount(
      <MatchPanel
        slug="cup"
        operations={view({ running: operation({ kind: "parse" }) })}
        pending={0}
        onChanged={() => {}}
      />,
    );
    await settle();

    expect(labelled(t("match.run"))?.disabled).toBe(true);
    expect(text()).toContain(t("operation.busy", { kind: t("operation.kind.parse") }));
  });

  it("reports the outcome of its own kind's last run", async () => {
    mount(
      <MatchPanel
        slug="cup"
        operations={view({
          concluded: {
            match: operation({
              kind: "match",
              status: "done",
              finished_at: "2026-04-01T14:40:00Z",
              outcome: { matched: 7, unmatched: 2 },
            }),
          },
        })}
        pending={0}
        onChanged={() => {}}
      />,
    );
    await settle();

    expect(text()).toContain(t("match.runResult", { matched: 7, unmatched: 2 }));
    // and the action is available again
    expect(labelled(t("match.run"))?.disabled).toBe(false);
  });

  it("reads an interruption as unfinished work rather than an error", async () => {
    mount(
      <DedupPanel
        slug="cup"
        operations={view({
          concluded: {
            dedup: operation({
              kind: "dedup",
              status: "interrupted",
              total: 8,
              done: 3,
              finished_at: "2026-04-01T14:40:00Z",
            }),
          },
        })}
        onChanged={() => {}}
      />,
    );
    await settle();

    const wording = t("operation.interrupted", {
      kind: t("operation.kind.dedup"),
      done: 3,
      total: 8,
    });
    expect(text()).toContain(wording);
    // stated as a hint, not as the error style — interruption is not failure
    expect(host?.querySelector(".login-error")).toBeNull();
  });

  it("reports a failure in the error style", async () => {
    mount(
      <ImportPanel
        slug="cup"
        operations={view({
          concluded: {
            parse: operation({
              status: "failed",
              finished_at: "2026-04-01T14:40:00Z",
              outcome: { error: "the model is unreachable" },
            }),
          },
        })}
        onImported={() => {}}
      />,
    );
    await settle();

    expect(host?.querySelector(".login-error")?.textContent).toContain("unreachable");
  });
});

/** A component with no markup of its own, so the hook's behaviour can be
 *  asserted without a panel in the way. */
function Probe({ onLanded }: { onLanded: (kind: string) => void }) {
  const operations = useOperations("cup", onLanded);
  return <span>{operations.running ? operations.running.kind : "idle"}</span>;
}

describe("the console's one poll", () => {
  it("asks again while work runs and stops once it lands", async () => {
    vi.useFakeTimers();
    const running: OperationsReport = { running: operation(), concluded: [] };
    const idle: OperationsReport = { running: null, concluded: [] };
    const operations = vi
      .spyOn(api, "operations")
      .mockResolvedValueOnce(running)
      .mockResolvedValue(idle);

    const probe = document.createElement("div");
    host = probe;
    document.body.append(probe);
    act(() => createRoot(probe).render(<Probe onLanded={() => {}} />));
    await act(async () => {});
    expect(text()).toBe("parse");

    // the poll ticks while something is running...
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(operations).toHaveBeenCalledTimes(2);
    expect(text()).toBe("idle");

    // ...and stops asking once nothing is
    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(operations).toHaveBeenCalledTimes(2);
  });

  it("reports a landing once, so the fencer list reloads without a refresh", async () => {
    vi.useFakeTimers();
    const landed = vi.fn();
    vi.spyOn(api, "operations")
      .mockResolvedValueOnce({ running: operation(), concluded: [] })
      .mockResolvedValue({
        running: null,
        concluded: [operation({ status: "done", finished_at: "2026-04-01T14:40:00Z" })],
      });

    const probe = document.createElement("div");
    host = probe;
    document.body.append(probe);
    act(() => createRoot(probe).render(<Probe onLanded={landed} />));
    await act(async () => {});
    expect(landed).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(landed.mock.calls).toEqual([["parse"]]);
  });
});
