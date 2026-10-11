import { slugHash } from "./slugHash";

// Deterministic tilt so the same record always renders the same stamp angle (spec section 4).
export function stampRotation(id: string | number): number {
  const normalized = (slugHash(String(id)) % 401) / 100; // 0..4
  return normalized - 2; // -2..+2
}

export default function PaidStamp({ id, label }: { id: string | number; label: string }) {
  return (
    <span className="stamp-paid" style={{ transform: `rotate(${stampRotation(id)}deg)` }}>
      {label}
    </span>
  );
}
