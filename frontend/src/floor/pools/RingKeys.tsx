import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import CopyButton from "../../CopyButton";
import * as routes from "../../routes";
import { poolsApi } from "../floorApi";

type Issued = { piste: number; link: string; qr: string };

/** The piste screens' links, one per piste: issue (which revokes the
 *  previous), copy, show as a QR code, revoke (spec floor-ring). A link's
 *  key is shown once, when issued. Placed on the Skupiny tab, where the
 *  pistes' work is (design add-floor-pools, task 4.3). */
export function RingKeys({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [pistes, setPistes] = useState<
    { piste_id: number; name: string; issued_at: string | null }[]
  >([]);
  const [issued, setIssued] = useState<Issued | null>(null);

  const load = useCallback(() => {
    poolsApi.ringKeys(slug).then(setPistes, () => setPistes([]));
  }, [slug]);
  useEffect(load, [load]);

  async function issue(piste: number) {
    const { key, qr_png_base64 } = await poolsApi.issue(slug, piste);
    setIssued({
      piste,
      link: `${window.location.origin}${routes.ringPath(piste, key)}`,
      qr: qr_png_base64,
    });
    load();
  }

  return (
    <section className="rail-card">
      <h2>{t("floor.ring.title")}</h2>
      <ul className="floor-pins">
        {pistes.map((piste) => (
          <li key={piste.piste_id}>
            {piste.name}: {piste.issued_at === null ? t("floor.ring.none") : t("floor.ring.live")}{" "}
            <button type="button" className="secondary" onClick={() => void issue(piste.piste_id)}>
              {piste.issued_at === null ? t("floor.ring.issue") : t("floor.ring.reissue")}
            </button>{" "}
            {piste.issued_at !== null && (
              <button
                type="button"
                className="secondary"
                onClick={() => void poolsApi.revoke(slug, piste.piste_id).then(load)}
              >
                {t("floor.ring.revoke")}
              </button>
            )}
            {issued?.piste === piste.piste_id && (
              <div className="floor-ring-issued">
                <code>{issued.link}</code>{" "}
                <CopyButton
                  value={issued.link}
                  label={t("common.copy")}
                  done={t("common.copied")}
                />
                <img
                  src={`data:image/png;base64,${issued.qr}`}
                  alt={t("floor.ring.qr", { name: piste.name })}
                  width={160}
                  height={160}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
