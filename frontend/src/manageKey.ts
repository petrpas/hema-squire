import { createContext, useContext } from "react";
import type { ManageKey } from "./api";

/** The manage key the page was opened with, on a guest's manage screen (spec
 *  `guest-registration`, design D8). Every `my-registration` call beneath the
 *  detail page presents it, so the management view is one surface for a guest
 *  and an account alike. Null everywhere else.
 *
 *  Never written to `localStorage`: the key lives in the URL the guest
 *  bookmarked or was mailed. */
export const ManageKeyContext = createContext<ManageKey>(null);

export function useManageKey(): ManageKey {
  return useContext(ManageKeyContext);
}
