import type { PleaQueueItem } from "../api";
import PleaQueue from "./PleaQueue";
import SharedHrIds from "./SharedHrIds";
import type { SharedHrGroup } from "./sharedHr";

/** What waits on an admin's decision (spec user-roles, Admin panel). */
export default function TasksTab({
  pleas,
  sharedHr,
  onChanged,
}: {
  pleas: PleaQueueItem[];
  sharedHr: SharedHrGroup[];
  onChanged: () => void;
}) {
  return (
    <>
      <PleaQueue pleas={pleas} onChanged={onChanged} />
      <SharedHrIds groups={sharedHr} onChanged={onChanged} />
    </>
  );
}
