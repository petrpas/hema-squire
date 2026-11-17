import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { publicFloorApi } from "../floorApi";

/** The signed-in fencer's own pools and bouts on the day, with piste and
 *  time; drawn only where there is something to show (spec floor-public). */
export function Itinerary({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<Awaited<ReturnType<typeof publicFloorApi.itinerary>>>([]);
  useEffect(() => {
    publicFloorApi.itinerary(slug).then(setItems, () => setItems([]));
  }, [slug]);
  if (items.length === 0) return null;
  return (
    <section className="rail-card floor-itinerary">
      <h2>{t("floor.public.itinerary")}</h2>
      <ul>
        {items.map((item) => (
          <li key={`${item.kind}-${item.discipline}-${item.number}`}>
            {item.discipline}:{" "}
            {item.kind === "pool"
              ? t("floor.public.pool", { number: item.number })
              : t("floor.public.round", { round: item.number })}
            {item.piste && `, ${t("floor.ring.piste", { name: item.piste })}`}
            {item.start && `, ${item.start}`}
          </li>
        ))}
      </ul>
    </section>
  );
}
