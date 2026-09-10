import type { TFunction } from "i18next";

import type { Operation, OperationKind } from "./api";

/** Counted progress, in the units the organizer recognises: an import is
 *  measured in rows, matching and deduplication in questions asked. Text, not
 *  a bar — the design spec allows no animated progress (CLAUDE.md). */
export function progressText(t: TFunction, operation: Operation): string {
  // parse and statement count rows; match and dedup count questions asked
  const key =
    operation.kind === "parse" || operation.kind === "statement"
      ? "operation.progress"
      : "operation.questions";
  return t(key, { count: operation.total, done: operation.done });
}

/** The clock time an operation started, in the reader's own zone: it is a
 *  moment in this session, not a moment in the tournament's calendar. */
export function startedText(t: TFunction, operation: Operation): string {
  const started = new Date(operation.started_at);
  return t("operation.started", {
    time: started.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
  });
}

/** When a concluded operation finished, read in the reader's own zone as
 *  `startedText` is and for the same reason: it is a moment in this session,
 *  not a moment in the tournament's calendar.
 *
 *  Load-bearing rather than decorative. The panels show the most recent
 *  concluded run of each kind with no bound on its age, so that an organizer
 *  who was not watching still learns what landed — and a report with no moment
 *  on it reads the same after four days as after four minutes. One was being
 *  read as the result of an intake that had just been run.
 *
 *  The day is dropped for a run that concluded today, which is the common case
 *  and the one where a date says nothing.
 */
export function concludedMoment(operation: Operation): string {
  if (operation.finished_at === null) return "";
  const at = new Date(operation.finished_at);
  if (Number.isNaN(at.getTime())) return "";
  const clock = at.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const today = new Date();
  const sameDay =
    at.getFullYear() === today.getFullYear() &&
    at.getMonth() === today.getMonth() &&
    at.getDate() === today.getDate();
  return sameDay ? clock : `${at.toLocaleDateString("cs")} ${clock}`;
}

export function kindName(t: TFunction, kind: OperationKind): string {
  return t(`operation.kind.${kind}`);
}

/** What a concluded operation has to say for itself, where the panel does not
 *  render its own outcome: a failure and an interruption read differently, and
 *  an interruption is not an error (spec console-operations, Interruption is
 *  not failure). */
export function conclusionText(t: TFunction, operation: Operation): string | null {
  const kind = kindName(t, operation.kind);
  if (operation.status === "failed") {
    const error = operation.outcome.error;
    return t("operation.failed", { kind, error: typeof error === "string" ? error : "" });
  }
  if (operation.status === "interrupted") {
    return t("operation.interrupted", {
      kind,
      done: operation.done,
      total: operation.total,
    });
  }
  return null;
}
