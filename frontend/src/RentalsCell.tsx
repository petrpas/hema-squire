import { useId } from "react";
import { useTranslation } from "react-i18next";

/** The items a row borrows, and which of them nothing is charging for.
 *
 *  A rental is billed through the item the tournament lends by that name. A
 *  name matching none of them is billed nothing at all — which is how thirty
 *  two borrowed weapons reached the pilot's roster with 1 600 Kč in no total
 *  anywhere — and a total that is quietly short is not something an organizer
 *  can find by reading the table.
 *
 *  So the name says so where it is listed. The marking is the italic the
 *  fencer list already uses for a value with another source, plus `HelpHint`'s
 *  box on hover: the row states what the fencer asked for, and the sentence
 *  explaining that nothing prices it opens where it is asked for. Nothing is
 *  removed from the cell — the fencer did ask to borrow it, and the remedy is
 *  the organizer's, usually a rental item they have not offered yet.
 */
export default function RentalsCell({
  rentals,
  unpriced,
}: {
  rentals: string[];
  unpriced: string[];
}) {
  if (rentals.length === 0) return <>—</>;
  return (
    <>
      {rentals.map((name, index) => (
        <span key={name}>
          {index > 0 && ", "}
          {unpriced.includes(name) ? <UnpricedRental name={name} /> : name}
        </span>
      ))}
    </>
  );
}

function UnpricedRental({ name }: { name: string }) {
  const { t } = useTranslation();
  const hintId = useId();
  return (
    <span className="help-hint">
      {/* biome-ignore lint/a11y/noNoninteractiveTabindex: a tooltip trigger must be focusable to be read, and activates nothing */}
      <span className="unpriced-rental" tabIndex={0} aria-describedby={hintId}>
        {name}
      </span>
      <span role="tooltip" id={hintId} className="help-hint-box">
        {t("console.unpriced_rental")}
      </span>
    </span>
  );
}
