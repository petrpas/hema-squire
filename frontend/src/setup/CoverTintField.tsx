import { useTranslation } from "react-i18next";

import type { CoverTint } from "../api";

const TINTS: readonly CoverTint[] = ["blue", "green", "yellow"];

/** Beside the logo in Setup: which of the three pastel tints the cover wears
 *  — following the logo, or one the organizer chooses (spec
 *  tournament-admin, The organizer chooses the cover tint). Only the three
 *  tint tokens are offered; no color is taken from anywhere else. */
export default function CoverTintField({
  slug,
  value,
  followed,
  onChange,
}: {
  slug: string;
  /** The organizer's choice; null follows the logo. */
  value: CoverTint | null;
  /** What following the logo gives now, named on that option so the choice
   *  is made knowing it. */
  followed: CoverTint;
  onChange: (value: CoverTint | null) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="form-field qualification-control">
      <span>{t("setup.identity.coverTint")}</span>
      <label className="qualification-option">
        <input
          type="radio"
          name={`${slug}-cover-tint`}
          checked={value === null}
          onChange={() => onChange(null)}
        />
        <span className="tint-swatch" data-tint={followed} aria-hidden="true" />
        {t("setup.identity.coverTintFollows", {
          tint: t(`setup.identity.coverTintName.${followed}`),
        })}
      </label>
      {TINTS.map((tint) => (
        <label key={tint} className="qualification-option">
          <input
            type="radio"
            name={`${slug}-cover-tint`}
            checked={value === tint}
            onChange={() => onChange(tint)}
          />
          <span className="tint-swatch" data-tint={tint} aria-hidden="true" />
          {t(`setup.identity.coverTintName.${tint}`)}
        </label>
      ))}
    </div>
  );
}
