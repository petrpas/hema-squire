/** A fencer's fixed number within the tournament, written the one way it is
 *  written everywhere: `#23`, in the data face and faded ink. The mark and the
 *  face are what set it apart from a position, which counts rows and is the
 *  table's own reading of itself (spec etl-console, Fixed fencer number). */
export default function FencerNumber({ number }: { number: number | null | undefined }) {
  return <span className="fencer-number">{fencerNumberText(number)}</span>;
}

/** The number as text, for the places that compose a sentence around it. */
export function fencerNumberText(number: number | null | undefined): string {
  return number === null || number === undefined ? "—" : `#${number}`;
}
