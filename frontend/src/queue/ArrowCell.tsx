import { IconArrowDown, IconArrowUp } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import { seatedIn } from "./queueColumns";

/** The one action a Queue row carries, where the server would carry it out
 *  (design queue-rosters D2): ↑ promotes a queued row while its discipline has
 *  a free place, ↓ returns a seated row while its registration is unpaid.
 *
 *  A row with no registration behind it holds no seat and is in no queue, so
 *  it carries neither and says so. The server stays the authority: a refusal
 *  that still happens — another organizer acting first — is reported by the
 *  phase, in words. */
export default function ArrowCell({
  row,
  slug,
  freeBySlug,
  busy,
  onPromote,
  onReturn,
}: {
  row: SheetRow;
  slug: string;
  /** Free places per individual discipline: a registration waiting on its
   *  participation condition is promoted only while every discipline of it has
   *  one (spec seating-queue, A conditional registration moves as one). */
  freeBySlug: Record<string, number>;
  busy: boolean;
  onPromote: (registrationId: number) => void;
  onReturn: (registrationId: number) => void;
}) {
  const { t } = useTranslation();
  const registrationId = row.registration_id;
  if (registrationId === null) return <span className="muted">{t("queue.noArrow")}</span>;

  if (seatedIn(row, slug)) {
    if (row.paid) return null;
    return (
      <button
        type="button"
        className="row-action"
        title={
          (row.conditional ?? []).includes(slug)
            ? t("queue.returnConditionHint")
            : t("queue.returnHint")
        }
        disabled={busy}
        onClick={() => onReturn(registrationId)}
      >
        <IconArrowDown size={16} stroke={1.5} />
        <span className="visually-hidden">{t("queue.returnToQueue")}</span>
      </button>
    );
  }

  if (promotionBlocked(row, slug, freeBySlug)) return null;
  return (
    <button
      type="button"
      className="row-action"
      title={t("queue.promoteHint")}
      disabled={busy}
      onClick={() => onPromote(registrationId)}
    >
      <IconArrowUp size={16} stroke={1.5} />
      <span className="visually-hidden">{t("queue.promote")}</span>
    </button>
  );
}

/** Whether promoting this queued row would be refused for want of a place: in
 *  its own discipline, or — where its registration waits on an unmet condition
 *  — in any discipline of the condition, all of which it would be seated in. */
export function promotionBlocked(
  row: SheetRow,
  slug: string,
  freeBySlug: Record<string, number>,
): boolean {
  const waitsWhole = (row.conditional ?? []).length > 0 && (row.disciplines ?? []).length === 0;
  const needed = waitsWhole ? new Set([slug, ...(row.conditional ?? [])]) : new Set([slug]);
  return [...needed].some((needs) => (freeBySlug[needs] ?? 0) <= 0);
}
