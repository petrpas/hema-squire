import { IconSearch } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { SheetRow } from "./api";

/** The verdict register of a Matching row: what the system concluded, and the
 *  two things the organizer can do about it.
 *
 *  Ratifying costs one click on the badge itself (spec `etl-console`, The
 *  ledger idiom). Nothing guards it: a resolution is a rule, and removing the
 *  rule undoes it, so a modal here would cost more than the mistake. Where
 *  there is no proposal to ratify the badge opens the search instead, which is
 *  the only action such a row has.
 */

const TAGS: Record<string, string> = {
  confirmed: "tag tag-seal-green",
  found: "tag tag-seal-green",
  proposed: "tag tag-form-yellow",
};

const LABELS: Record<string, string> = {
  confirmed: "match.verdict.confirmed",
  found: "match.verdict.found",
  proposed: "match.verdict.proposed",
  none_found: "match.verdict.noneFound",
  unknown: "match.verdict.unknown",
};

/** The verdicts a machine reached, which an organizer's confirmation turns
 *  into their own. A confirmed row has nothing left to ratify. */
export function isRatifiable(verdict: string | undefined): boolean {
  return verdict === "proposed" || verdict === "found";
}

export default function MatchCell({
  row,
  onRatify,
  onSearch,
}: {
  row: SheetRow;
  onRatify: () => void;
  onSearch: () => void;
}) {
  const { t } = useTranslation();
  const verdict = row.match_verdict ?? "unknown";
  const ratifiable = isRatifiable(verdict) && row.hr_id !== null;
  const disabled = row._deleted === true;
  const label = t(LABELS[verdict] ?? LABELS.unknown);

  return (
    <span className="match-cell">
      <button
        className="badge-button"
        title={ratifiable ? t("match.ratify") : t("match.title")}
        onClick={ratifiable ? onRatify : onSearch}
        disabled={disabled}
      >
        {TAGS[verdict] ? (
          <span className={TAGS[verdict]}>{label}</span>
        ) : (
          <span className="state-text">{label}</span>
        )}
      </button>
      {ratifiable && (
        <button
          className="row-action"
          title={t("match.search")}
          onClick={onSearch}
          disabled={disabled}
        >
          <IconSearch size={14} stroke={1.5} />
        </button>
      )}
    </span>
  );
}
