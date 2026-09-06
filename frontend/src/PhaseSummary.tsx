import { IconRefresh } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

/** What a phase says about itself in its header, beside its title: how much of
 *  its own work is still waiting, and the button that asks the server again.
 *
 *  The line states outstanding work rather than size — the document footer
 *  already gives the size, and a header repeating it would say one thing twice.
 *  Zero is stated as plainly as five: a header that appeared only when there
 *  was work would move the title every time the last decision was made, and
 *  "nothing is waiting" is the answer the organizer came for as often as any
 *  other (spec `etl-console`, Deduplication candidate review, where this began).
 *
 *  The button reads as refreshing the count it sits behind, which is what it
 *  does — the count is a reading of the same sheet the table draws. Small and
 *  unlettered, because it is not the phase's work: an icon at the end of a line
 *  of text, not a control competing with the title.
 */
export default function PhaseSummary({
  text,
  onRefresh,
}: {
  /** The phase's own line, or null for a phase that has not been given one —
   *  it keeps the button, which is what the header is for. */
  text: string | null;
  onRefresh: () => void;
}) {
  const { t } = useTranslation();
  return (
    <span className="phase-summary">
      {text !== null && <span className="phase-count">{text}</span>}
      <button
        type="button"
        className="phase-refresh"
        onClick={onRefresh}
        title={t("console.refresh")}
        aria-label={t("console.refresh")}
      >
        <IconRefresh size={15} stroke={1.5} aria-hidden />
      </button>
    </span>
  );
}
