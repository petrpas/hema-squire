import { slugHash } from "./slugHash";

// Deterministic tilt so the same record always renders the same stamp angle (spec section 4).
export function stampRotation(id: string | number): number {
  const normalized = (slugHash(String(id)) % 401) / 100; // 0..4
  return normalized - 2; // -2..+2
}

/** `muted` draws the same mark in a faded ink: the shape of a stamp without
 *  the one saturated colour, for a mark that states money but not payment. */
export default function PaidStamp({
  id,
  label,
  muted = false,
}: {
  id: string | number;
  label: string;
  muted?: boolean;
}) {
  return (
    <span
      className={muted ? "stamp-paid stamp-muted" : "stamp-paid"}
      style={{ transform: `rotate(${stampRotation(id)}deg)` }}
    >
      {label}
    </span>
  );
}
