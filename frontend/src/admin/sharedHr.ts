import type { AdminAccount } from "../api";

export interface SharedHrGroup {
  hrId: number;
  accounts: AdminAccount[];
}

/** Every HR ID more than one account holds, with those accounts (design D3).
 *  Derived from the account list, whose `hr_shared` already says which
 *  accounts are concerned; ordered by HR ID so the list holds still while the
 *  admin works through it. */
export function sharedHrGroups(accounts: AdminAccount[]): SharedHrGroup[] {
  const groups = new Map<number, AdminAccount[]>();
  for (const account of accounts) {
    if (account.hr_id === null || !account.hr_shared) continue;
    groups.set(account.hr_id, [...(groups.get(account.hr_id) ?? []), account]);
  }
  return [...groups.entries()]
    .filter(([, holders]) => holders.length > 1)
    .sort(([a], [b]) => a - b)
    .map(([hrId, holders]) => ({ hrId, accounts: holders }));
}
