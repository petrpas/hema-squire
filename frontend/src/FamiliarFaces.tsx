import { useTranslation } from "react-i18next";
import type { Familiar } from "./api";

/** The tints the faces wear, by position, so neighbours differ. */
const FACE_TINTS = ["blue", "green", "yellow"] as const;

/** The left side of a card's foot for a signed-in visitor (spec `fencer-home`,
 *  A card names familiar faces to a signed-in visitor): up to three
 *  overlapping faces bearing initials, then a note saying who they are. The
 *  note claims a ranking only where the order follows one. */
export default function FamiliarFaces({ familiar }: { familiar: Familiar }) {
  const { t } = useTranslation();
  const note =
    familiar.basis === "club"
      ? t("home.familiar.club", { count: familiar.total })
      : familiar.ranked
        ? t("home.familiar.countryRanked", { country: familiar.country })
        : t("home.familiar.country", { count: familiar.total, country: familiar.country });
  return (
    <span className="familiar">
      <span className="familiar-faces">
        {familiar.people.map((person, index) => (
          <span
            // biome-ignore lint/suspicious/noArrayIndexKey: a read-only list rebuilt from props; two people may share initials and a label
            key={index}
            className="familiar-face"
            data-tint={FACE_TINTS[index % FACE_TINTS.length]}
            role="img"
            aria-label={person.label}
            title={person.label}
          >
            {person.initials}
          </span>
        ))}
      </span>
      <span className="familiar-note">{note}</span>
    </span>
  );
}
