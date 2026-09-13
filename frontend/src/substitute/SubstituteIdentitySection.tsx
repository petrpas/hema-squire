import { useTranslation } from "react-i18next";
import type { HRProfile } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HRSearchPicker from "../HRSearch";
import type { FieldError as FieldErrorValue } from "../validation";

/** Who is taking the seat: a name, and the HEMA Ratings profile behind it where
 *  there is one.
 *
 *  The profile is offered and not required. A fencer the index does not carry
 *  is a substitute like any other, and their row travels through matching
 *  exactly as a hand-entered one does (spec `fencer-substitution`, The
 *  substitute is named through the HEMA Ratings index). The picker is the same
 *  one the profile page and account creation use, searching by the name already
 *  typed above, so the name is written once. */
export default function SubstituteIdentitySection({
  name,
  onName,
  profile,
  onProfile,
  error,
  onBlur,
}: {
  name: string;
  onName: (value: string) => void;
  profile: HRProfile | null;
  onProfile: (profile: HRProfile | null) => void;
  error: FieldErrorValue | undefined;
  onBlur: () => void;
}) {
  const { t } = useTranslation();

  return (
    <>
      <label className="form-field">
        <span>{t("column.name")}</span>
        <input
          value={name}
          onChange={(event) => onName(event.target.value)}
          onBlur={onBlur}
          {...invalidProps("name", error)}
        />
        <FieldError field="name" error={error} />
      </label>

      {/* The label is a label and the sentence under it is a sentence. Kept
          out of the `.form-field` above, whose own casing is the label's: an
          explanation set in the label's capitals reads as a second heading. */}
      <div className="substitute-profile">
        <span className="form-label">{t("substitute.profile")}</span>
        {profile === null ? (
          <>
            <p className="rail-hint">{t("substitute.profileOptional")}</p>
            {/* the name above is the query: a second name field would be a
                second answer to one question */}
            <HRSearchPicker lockedQuery={name} onConfirm={onProfile} />
          </>
        ) : (
          <>
            <p className="substitute-profile-chosen">
              {profile.name}
              {profile.club ? ` — ${profile.club}` : ""}
              {profile.nationality ? ` (${profile.nationality})` : ""}
            </p>
            <button type="button" className="secondary" onClick={() => onProfile(null)}>
              {t("substitute.clearProfile")}
            </button>
          </>
        )}
      </div>
    </>
  );
}
