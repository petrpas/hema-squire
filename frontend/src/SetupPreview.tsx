import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Availability, type TournamentDetail as TournamentDetailData, api } from "./api";
import {
  DiscountList,
  DisciplinesInfo,
  InfoHeader,
  OtherActionsInfo,
  RegistrationForm,
} from "./TournamentFace";

type PreviewTab = "face" | "form";

export default function SetupPreview({
  detail,
  slug,
}: {
  detail: TournamentDetailData;
  slug: string;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<PreviewTab>("face");
  const [availability, setAvailability] = useState<Availability[]>([]);

  useEffect(() => {
    api.availability(slug).then(setAvailability, () => setAvailability([]));
  }, [slug, detail]);

  return (
    <div className="setup-preview">
      <p className="setup-preview-heading">{t("preview.heading")}</p>
      <nav className="stage-control preview-tabs">
        <button className={tab === "face" ? "active" : ""} onClick={() => setTab("face")}>
          {t("preview.tabs.face")}
        </button>
        <button className={tab === "form" ? "active" : ""} onClick={() => setTab("form")}>
          {t("preview.tabs.form")}
        </button>
      </nav>
      {tab === "face" ? (
        <>
          <InfoHeader detail={detail} />
          <DisciplinesInfo detail={detail} availability={availability} />
          <DiscountList detail={detail} />
          <OtherActionsInfo detail={detail} />
        </>
      ) : (
        <RegistrationForm detail={detail} availability={availability} mode={{ kind: "preview" }} />
      )}
    </div>
  );
}
