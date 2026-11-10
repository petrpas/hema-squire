import type { AdminDeferredDeletion, PleaQueueItem } from "../api";
import DeferredDeletions from "./DeferredDeletions";
import PleaQueue from "./PleaQueue";
import SharedHrIds from "./SharedHrIds";
import type { SharedHrGroup } from "./sharedHr";

/** What waits on an admin's decision (spec user-roles, Admin panel). */
export default function TasksTab({
  pleas,
  sharedHr,
  deletions,
  onChanged,
}: {
  pleas: PleaQueueItem[];
  sharedHr: SharedHrGroup[];
  deletions: AdminDeferredDeletion[];
  onChanged: () => void;
}) {
  return (
    <>
      <PleaQueue pleas={pleas} onChanged={onChanged} />
      <SharedHrIds groups={sharedHr} onChanged={onChanged} />
      <DeferredDeletions deletions={deletions} />
    </>
  );
}
