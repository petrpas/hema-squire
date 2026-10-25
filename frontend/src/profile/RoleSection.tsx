import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, api, type Plea } from "../api";
import PleaSection from "../PleaSection";

export default function RoleSection({ account }: { account: Account }) {
  const { t } = useTranslation();
  const [plea, setPlea] = useState<Plea | null>(null);
  const isPlainFencer = account.role === "fencer" && !account.is_deployment_owner;

  useEffect(() => {
    if (isPlainFencer) api.myPlea().then(setPlea, () => setPlea(null));
  }, [isPlainFencer]);

  const roleLabel = account.is_deployment_owner
    ? t("admin.accounts.owner")
    : t(`admin.accounts.roles.${account.role}`);

  return (
    <section className="rail-card">
      <h2>{t("profile.role.title")}</h2>
      <p className="tag tag-file-blue role-section-tag">{roleLabel}</p>
      {isPlainFencer && plea && <PleaSection plea={plea} onPleaChange={setPlea} />}
    </section>
  );
}
