import type { RosterMemberFields, RosterMemberInput, TeamEntry } from "./api";

/** One row of a roster draft: a stored member carries the identity the server
 *  issued, a member not yet saved carries none. */
export interface DraftRosterMember extends RosterMemberFields {
  id: number | null;
}

/** A draft row as React holds it. A stored member's identity is the server's
 *  `id`; a member added but not yet saved has none, and needs `rowId` until it
 *  does — two members may share every field, and a row that is removed or
 *  moved up must not hand its open name field to whichever member takes its
 *  place. */
export interface DraftRow extends DraftRosterMember {
  rowId: string;
}

let nextRowId = 0;

export function draftRow(member: RosterMemberFields & { id?: number | null }): DraftRow {
  return { ...member, id: member.id ?? null, rowId: `row-${nextRowId++}` };
}

/** What one draft row says to the server: the member it is about, where it has
 *  one, and the four stored fields. Order is the position in the list sent,
 *  which identifies nobody. */
export function toRosterInput(member: DraftRosterMember): RosterMemberInput {
  return {
    id: member.id,
    name: member.name,
    hr_id: member.hr_id,
    club: member.club,
    nationality: member.nationality,
  };
}

/** Order-sensitive: a roster is a list, so a reorder is a real change
 *  (design D3). Compares every field the editor can alter. */
export function rosterChanged(saved: RosterMemberFields[], draft: RosterMemberFields[]): boolean {
  if (saved.length !== draft.length) return true;
  return saved.some((member, index) => {
    const next = draft[index];
    if (!next) return true;
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
export function summarizeSaves(outcomes: RosterSaveOutcome[]): {
  saved: TeamEntry[];
  failed: string[];
} {
  const saved: TeamEntry[] = [];
  const failed: string[] = [];
  for (const { team, result } of outcomes) {
    if (result.status === "fulfilled") saved.push(result.value);
    else failed.push(team.name);
  }
  return { saved, failed };
}
