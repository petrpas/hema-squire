import { type CoverTint, logoUrl } from "./api";
import { monogram } from "./monogram";
import { slugHash } from "./slugHash";

/** What a cover and a plate read off a tournament, whichever payload carries
 *  it: a list entry or a detail. */
export interface CoverSubject {
  slug: string;
  display_name: string;
  has_logo: boolean;
  logo_tint: "blue" | "green" | "warm" | null;
  cover_tint: CoverTint | null;
  short_code: string | null;
}

const SLUG_TINTS: readonly CoverTint[] = ["blue", "green", "yellow"];

/** The cover's tint (spec `fencer-home`, A card's cover tint follows its
 *  logo): the one the organizer chose where they chose one; else the logo's
 *  hue band where it has one — the warm band wears the only warm tint,
 *  form-yellow — and otherwise one chosen from the slug, so the same
 *  tournament wears the same cover on its card and on its page. */
export function coverTint(subject: CoverSubject): CoverTint {
  if (subject.cover_tint) return subject.cover_tint;
  if (subject.logo_tint === "warm") return "yellow";
  if (subject.logo_tint !== null) return subject.logo_tint;
  return SLUG_TINTS[slugHash(subject.slug) % SLUG_TINTS.length] ?? "blue";
}

/** The logo where one is set, filling the plate; the organizer's short code
 *  or the derived monogram otherwise. `ring` draws the plate's outline —
 *  `open` in `--stamp` while registration is open — and is omitted where no
 *  ring belongs, beside a live figure. */
export function CoverPlate({
  subject,
  className,
  ring,
}: {
  subject: CoverSubject;
  className: string;
  ring?: "open" | "rest";
}) {
  return (
    <span className={className} data-logo={subject.has_logo || undefined} data-ring={ring}>
      {subject.has_logo ? (
        <img src={logoUrl(subject.slug)} alt="" />
      ) : (
        <span aria-hidden="true">{subject.short_code ?? monogram(subject.display_name)}</span>
      )}
    </span>
  );
}
