import { useId } from "react";
import { useTranslation } from "react-i18next";

/** What a hand-settled registration's balance reads.
 *
 *  Nothing was credited and nothing is due, so the figure the outstanding
 *  column would otherwise show is true of neither: the fencer owes the
 *  organizer nothing, and Squire received nothing. Showing the full total
 *  there reads as a fault in every roster it appears in, so the column says
 *  what is actually the case (spec etl-console).
 *
 *  **The word alone, and the reason on hover.** A reason is the organizer's
 *  own sentence and runs as long as one — *volný vstup za čtvrté místo
 *  dosažené v loňském roce* — and a money column set to the width of the
 *  longest of them stops being a money column. The cell states the fact, which
 *  is the same on every waived row and the only part the table is reading for;
 *  the sentence behind it opens where it is asked for.
 *
 *  The word is its own marker, in `HelpHint`'s idiom but carrying none of its
 *  marking — no glyph, no underline, no help cursor. The one word in a column
 *  of figures is conspicuous enough to be tried, and each of those would have
 *  been a second mark saying only that the first one has more behind it. A row
 *  waived without a reason — which the organizer may do where Squire collects
 *  nothing — has nothing to open at all.
 */
export default function WaivedBalance({ reason }: { reason: string | null }) {
  const { t } = useTranslation();
  const hintId = useId();
  const word = t("console.waived");

  if (!reason) return <span className="waived-balance">{word}</span>;

  return (
    <span className="help-hint waived-hint">
      <span className="waived-balance waived-marker" tabIndex={0} aria-describedby={hintId}>
        {word}
      </span>
      <span role="tooltip" id={hintId} className="help-hint-box">
        {reason}
      </span>
    </span>
  );
}
