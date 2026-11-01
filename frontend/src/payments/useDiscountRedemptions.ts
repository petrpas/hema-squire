import { useEffect, useState } from "react";

import { api, type DiscountCodeRedemptions } from "../api";

export interface RedemptionsLoad {
  data: DiscountCodeRedemptions | null;
  failed: boolean;
}

/** Who holds which code. Its own request, so that it failing leaves the phase's
 *  other tables as they were (spec payments-console). */
export function useDiscountRedemptions(
  slug: string,
  reload: number,
  active: boolean,
): RedemptionsLoad {
  const [load, setLoad] = useState<RedemptionsLoad>({ data: null, failed: false });

  useEffect(() => {
    if (!active) return;
    api.discountCodeRedemptions(slug).then(
      (data) => setLoad({ data, failed: false }),
      () => setLoad({ data: null, failed: true }),
    );
  }, [slug, reload, active]);

  return load;
}
