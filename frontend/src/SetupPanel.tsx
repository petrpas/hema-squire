import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";

import { type Account, type TournamentDetail, api } from "./api";
import { CurrencySection } from "./setup/CurrencySection";
import { DangerZoneSection } from "./setup/DangerZoneSection";
import { DiscountsSection } from "./setup/DiscountsSection";
import { DisciplinesSection } from "./setup/DisciplinesSection";
import { ExtraItemsSection } from "./setup/ExtraItemsSection";
import { IdentitySection, VsSeriesSection } from "./setup/IdentitySection";
import { OrganizersSection } from "./setup/OrganizersSection";
import { PublishSection } from "./setup/PublishSection";
import { MISSING_TAB, SaverRegistry, SETUP_TABS, type SetupTab } from "./setup/shared";
import { SetupSaveBar } from "./setup/SetupSaveBar";
import { SetupTabBar } from "./setup/SetupTabBar";
import { TeamSection } from "./setup/TeamSection";
import SetupPreview from "./SetupPreview";

export default function SetupPanel({
  detail,
  slug,
  onSaved,
  hasRegistrations,
  onDeleted,
  onDirtyChange,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
  hasRegistrations: boolean;
  onDeleted: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);
  const [tab, setTab] = useState<SetupTab>("tournament");
  const registry = useRef(new SaverRegistry()).current;
  useSyncExternalStore(registry.subscribe, registry.getVersion);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const totalPending = registry
    .all()
    .reduce((sum, entry) => sum + entry.saver.pendingCount, 0);

  useEffect(() => {
    onDirtyChange(totalPending > 0);
  }, [totalPending, onDirtyChange]);

  if (detail === null) return <p>{t("common.loading")}</p>;

  const isOwner = account !== null && account.id === detail.owner_id;
  const offeredTabs = isOwner ? SETUP_TABS : SETUP_TABS.filter((setupTab) => setupTab !== "other");
  const missing = detail.setup_missing ?? [];
  const markedTabs = new Set(
    missing
      .map((key) => MISSING_TAB[key])
      .filter((value): value is SetupTab => value !== undefined),
  );
  // PUBLISH carries a marker whenever any other tab does — it is where the
  // items are listed (design D7)
  if (markedTabs.size > 0) markedTabs.add("publish");

  return (
    <div className="setup-split">
      <div className="setup-panel">
        <div className="setup-panel-header">
          <SetupTabBar tabs={offeredTabs} tab={tab} onSelect={setTab} markedTabs={markedTabs} />
        </div>
        <div className="setup-panel-body">
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-tournament"
            role="tabpanel"
            aria-labelledby="setup-tab-tournament"
            hidden={tab !== "tournament"}
          >
            <IdentitySection detail={detail} slug={slug} onSaved={onSaved} registry={registry} />
            <OrganizersSection detail={detail} slug={slug} registry={registry} />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-disciplines"
            role="tabpanel"
            aria-labelledby="setup-tab-disciplines"
            hidden={tab !== "disciplines"}
          >
            <DisciplinesSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-extra"
            role="tabpanel"
            aria-labelledby="setup-tab-extra"
            hidden={tab !== "extra"}
          >
            <ExtraItemsSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-payments"
            role="tabpanel"
            aria-labelledby="setup-tab-payments"
            hidden={tab !== "payments"}
          >
            <CurrencySection detail={detail} slug={slug} registry={registry} />
            <VsSeriesSection detail={detail} />
            <DiscountsSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          {isOwner && (
            <div
              className="setup-tabpanel"
              id="setup-tabpanel-other"
              role="tabpanel"
              aria-labelledby="setup-tab-other"
              hidden={tab !== "other"}
            >
              <TeamSection slug={slug} />
              <DangerZoneSection
                slug={slug}
                hasRegistrations={hasRegistrations}
                cancelled={detail.cancelled_at !== null}
                onDeleted={onDeleted}
                onCancelled={onSaved}
              />
            </div>
          )}
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-publish"
            role="tabpanel"
            aria-labelledby="setup-tab-publish"
            hidden={tab !== "publish"}
          >
            <PublishSection
              slug={slug}
              detail={detail}
              hasUnsavedChanges={totalPending > 0}
              onPublished={onSaved}
            />
          </div>
          <SetupSaveBar
            tab={tab}
            registry={registry}
            hasRegistrations={hasRegistrations}
            onSaved={onSaved}
          />
        </div>
      </div>
      <SetupPreview detail={detail} slug={slug} />
    </div>
  );
}
