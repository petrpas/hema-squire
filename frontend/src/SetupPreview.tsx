import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Availability, api, type TournamentDetail as TournamentDetailData } from "./api";
import {
  DisciplinesInfo,
  DiscountList,
  InfoHeader,
  OtherActionsInfo,
  RegistrationForm,
} from "./TournamentFace";

type PreviewTab = "face" | "form";

export default function SetupPreview({
  detail,
  slug,
  shown = true,
  asTabPanel = false,
}: {
  detail: TournamentDetailData;
  slug: string;
  /** False while the settings pane's own preview tab is not selected. The
   *  preview stays mounted — its face and its form selections must survive —
   *  and only stops being displayed (setup-preview-tab D1). */
  shown?: boolean;
  /** Whether this is the panel of the settings pane's preview tab, rather
   *  than a pane beside the settings. */
  asTabPanel?: boolean;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<PreviewTab>("face");
  const [availability, setAvailability] = useState<Availability[]>([]);
  // A hidden element's scrollTop is not kept reliably across browsers, so the
  // position is followed as it scrolls and put back when the preview is shown
  // again (setup-preview-tab D2). It is read while scrolling rather than on
  // hiding, because by the time an effect learns of the hiding the element is
  // already out of layout and may report 0.
  const pane = useRef<HTMLDivElement>(null);
  const scrollTop = useRef(0);

  useLayoutEffect(() => {
    if (shown && pane.current !== null) pane.current.scrollTop = scrollTop.current;
  }, [shown]);

  useEffect(() => {
    api.availability(slug).then(setAvailability, () => setAvailability([]));
  }, [slug, detail]);

  return (
    <div
      ref={pane}
      className="setup-preview"
      hidden={!shown}
      onScroll={(event) => {
        scrollTop.current = event.currentTarget.scrollTop;
      }}
      {...(asTabPanel && {
        id: "setup-tabpanel-preview",
        role: "tabpanel",
        "aria-labelledby": "setup-tab-preview",
      })}
    >
      <p className="setup-preview-heading">{t("preview.heading")}</p>
      <nav className="stage-control preview-tabs">
        <button
          type="button"
          className={tab === "face" ? "active" : ""}
          onClick={() => setTab("face")}
        >
          {t("preview.tabs.face")}
        </button>
        <button
          type="button"
          className={tab === "form" ? "active" : ""}
          onClick={() => setTab("form")}
        >
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
