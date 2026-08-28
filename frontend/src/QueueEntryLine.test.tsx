// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";

import type { QueueEntry } from "./api";
import i18n from "./i18n";
import QueueEntryLine from "./QueueEntryLine";

// The queue is ordered by the registration moment, so the line has to state
// the moment it is ordered by — the day alone cannot separate two fencers who
// registered the same morning (spec `seating-queue`).

function entry(position: number, registeredAt: string): QueueEntry {
  return {
    registration_id: position,
    fencer: `Fencer ${position}`,
    club: null,
    vs: null,
    registered_at: registeredAt,
    queue_position: position,
  };
}

function line(entry: QueueEntry): string {
  return renderToStaticMarkup(<QueueEntryLine entry={entry} timezone="Europe/Prague" />);
}

describe("queue entry line", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("en");
  });

  it("separates two entries registered minutes apart on one day", () => {
    const first = line(entry(1, "2026-03-14T08:05:00Z"));
    const second = line(entry(2, "2026-03-14T08:41:00Z"));
    expect(first).toContain("registered 14. 3. 2026 09:05");
    expect(second).toContain("registered 14. 3. 2026 09:41");
  });

  it("reads the moment in the tournament's zone, not the reader's", () => {
    const html = renderToStaticMarkup(
      <QueueEntryLine entry={entry(1, "2026-03-14T23:30:00Z")} timezone="Pacific/Auckland" />,
    );
    expect(html).toContain("registered 15. 3. 2026 12:30");
  });
});
