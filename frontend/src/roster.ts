import { type RosterMember, type TeamEntry } from "./api";

/** Order-sensitive: a roster is a list, so a reorder is a real change
 *  (design D3). Compares every field the editor can alter. */
export function rosterChanged(saved: RosterMember[], draft: RosterMember[]): boolean {
  if (saved.length !== draft.length) return true;
  return saved.some((member, index) => {
    const next = draft[index];
    return (
      member.name !== next.name ||
      member.hr_id !== next.hr_id ||
      member.club !== next.club ||
      member.nationality !== next.nationality
    );
  });
}

/** One dirty team's settled save, paired with the team it was submitted for
 *  so a rejection can still be named. */
export interface RosterSaveOutcome {
  team: TeamEntry;
  result: PromiseSettledResult<TeamEntry>;
}

/** Splits a fan-out's settled results into the teams to push down as saved
 *  and the names of the teams that did not save (design D4). */
export function summarizeSaves(
  outcomes: RosterSaveOutcome[],
): { saved: TeamEntry[]; failed: string[] } {
  const saved: TeamEntry[] = [];
  const failed: string[] = [];
  for (const { team, result } of outcomes) {
    if (result.status === "fulfilled") saved.push(result.value);
    else failed.push(team.name);
  }
  return { saved, failed };
}
