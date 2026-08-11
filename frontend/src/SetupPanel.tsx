import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";

import { type Account, type TournamentDetail, api } from "./api";
import { BankAccountSection } from "./setup/BankAccountSection";
import { CurrencySection } from "./setup/CurrencySection";
import { DangerZoneSection } from "./setup/DangerZoneSection";
import { DiscountsSection } from "./setup/DiscountsSection";
import { DisciplinesSection } from "./setup/DisciplinesSection";
import { ExportSheetSection } from "./setup/ExportSheetSection";
import { ExtraItemsSection } from "./setup/ExtraItemsSection";
import { IdentitySection, VsSeriesSection } from "./setup/IdentitySection";
import { LegacyFeesSection } from "./setup/LegacyFeesSection";
import { ModeSection } from "./setup/ModeSection";
import { OrganizersSection } from "./setup/OrganizersSection";
import { PaymentModeSection } from "./setup/PaymentModeSection";
import { PublishSection } from "./setup/PublishSection";
import { missingTab, offeredSetupTabs, SaverRegistry, type SetupTab } from "./setup/shared";
import { SetupSaveBar } from "./setup/SetupSaveBar";
import { SetupTabBar } from "./setup/SetupTabBar";
import { TeamSection } from "./setup/TeamSection";
import { TimelineSection } from "./setup/TimelineSection";
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
  // TOURNAMENT is where Setup opens, and where it falls back to when the
  // selected tab stops being offered — turning extra services off while
  // EXTRA is open must not leave the pane on nothing.
  const [tab, setTab] = useState<SetupTab>("tournament");
  const registry = useRef(new SaverRegistry()).current;
  useSyncExternalStore(registry.subscribe, registry.getVersion);
  // Whether a team discipline exists in the DISCIPLINES draft, reported up by
  // that section so TIMELINE can offer the composition deadline before the
  // table is saved (design Decision 3a). Seeded from saved state so the first
  // render is right even before the section reports.
  const [hasTeamDiscipline, setHasTeamDiscipline] = useState(
    () => detail?.disciplines.some((discipline) => discipline.kind === "team") ?? false,
  );

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
  const offeredTabs = offeredSetupTabs(detail, isOwner);
  const selected = offeredTabs.includes(tab) ? tab : "tournament";
  const missing = detail.setup_missing ?? [];
  // A marker is only ever raised on a tab the mode offers: an item whose
  // editor the features conceal marks PUBLISH alone, which names the feature
  // that brings the editor back (spec: setup-navigation).
  const markedTabs = new Set(
    missing
      .map((key) => missingTab(key, detail))
      .filter((value): value is SetupTab => value !== undefined && offeredTabs.includes(value)),
  );
  // PUBLISH carries a marker whenever any other tab does — it is where the
  // items are listed (design D7)
  if (markedTabs.size > 0) markedTabs.add("publish");

  const dirtyTabs = new Set(
    offeredTabs.filter((setupTab) =>
      registry.forTab(setupTab).some((entry) => entry.saver.pendingCount > 0),
    ),
  );

  return (
    <div className="setup-split">
      <div className="setup-panel">
        <div className="setup-panel-header">
          <SetupTabBar
            tabs={offeredTabs}
            tab={selected}
            mode={detail}
            onSelect={setTab}
            markedTabs={markedTabs}
            dirtyTabs={dirtyTabs}
          />
        </div>
        <div className="setup-panel-body">
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-tournament"
            role="tabpanel"
            aria-labelledby="setup-tab-tournament"
            hidden={selected !== "tournament"}
          >
            <IdentitySection detail={detail} slug={slug} onSaved={onSaved} registry={registry} />
            <OrganizersSection detail={detail} slug={slug} registry={registry} />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-disciplines"
            role="tabpanel"
            aria-labelledby="setup-tab-disciplines"
            hidden={selected !== "disciplines"}
          >
            <DisciplinesSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
              onTeamKindChange={setHasTeamDiscipline}
            />
          </div>
          {/* a section whose feature is off is not rendered at all, so its
              saver never registers and no marker can be raised on a tab that
              is not in the bar (spec: setup-navigation) */}
          {detail.feature_extras && (
            <div
              className="setup-tabpanel"
              id="setup-tabpanel-extra"
              role="tabpanel"
              aria-labelledby="setup-tab-extra"
              hidden={selected !== "extra"}
            >
              <ExtraItemsSection
                detail={detail}
                slug={slug}
                pricingWarning={hasRegistrations}
                registry={registry}
              />
            </div>
          )}
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-timeline"
            role="tabpanel"
            aria-labelledby="setup-tab-timeline"
            hidden={selected !== "timeline"}
          >
            <TimelineSection
              detail={detail}
              slug={slug}
              registry={registry}
              hasTeamDiscipline={hasTeamDiscipline}
            />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-payments"
            role="tabpanel"
            aria-labelledby="setup-tab-payments"
            hidden={selected !== "payments"}
          >
            {/* while payments are off the tab is titled PRICING and holds
                only what survives that: the currency the tournament prices
                in, its discounts, and any legacy fixed fees it still carries
                (design D7) */}
            {detail.feature_payments && (
              <>
                <PaymentModeSection detail={detail} slug={slug} registry={registry} />
                <BankAccountSection detail={detail} slug={slug} registry={registry} />
              </>
            )}
            <CurrencySection detail={detail} slug={slug} registry={registry} />
            {detail.feature_payments && <VsSeriesSection detail={detail} />}
            <DiscountsSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
            <LegacyFeesSection detail={detail} slug={slug} onSaved={onSaved} />
          </div>
          {isOwner && (
            <div
              className="setup-tabpanel"
              id="setup-tabpanel-other"
              role="tabpanel"
              aria-labelledby="setup-tab-other"
              hidden={selected !== "other"}
            >
              <ModeSection detail={detail} onApplied={onSaved} />
              <TeamSection slug={slug} />
              <ExportSheetSection detail={detail} slug={slug} registry={registry} />
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
            hidden={selected !== "publish"}
          >
            <PublishSection
              slug={slug}
              detail={detail}
              hasUnsavedChanges={totalPending > 0}
              onPublished={onSaved}
            />
          </div>
          <SetupSaveBar
            tab={selected}
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
