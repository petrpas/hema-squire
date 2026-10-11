/** A small, stable hash of a string: the same input gives the same number on
 *  every render and every device. What the Paid stamp's tilt and a tournament
 *  card's cover tint are both derived from, so neither is random and neither
 *  needs storing. Non-negative. */
export function slugHash(s: string): number {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}
