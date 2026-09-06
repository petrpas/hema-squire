import { useTranslation } from "react-i18next";

/** What a phase shows on a draft, in place of its own body (spec etl-console,
 *  The console states what it is waiting for on a draft).
 *
 *  One statement, written to be true of every phase rather than one per phase
 *  saying the same thing differently, and rendered once in the phase's body
 *  rather than on the tab, on each panel and beside each control the phase
 *  would otherwise offer. The phase strip is untouched: what publication
 *  changes is the body, never the strip. */
export default function AwaitsPublication() {
  const { t } = useTranslation();
  return (
    <div className="sheet-scroll">
      <p className="sheet-empty">{t("console.awaitsPublication")}</p>
    </div>
  );
}
