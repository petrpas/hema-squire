import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type CoverGround, type CoverTint, coverPhotoUrl } from "../api";

const TINTS: readonly CoverTint[] = ["blue", "green", "yellow", "red"];

/** Beside the logo in Setup: what the cover stands on — following the logo,
 *  one of the four tints, or the tournament's cover photo (spec
 *  tournament-admin, The organizer chooses the cover ground). Only the tint
 *  tokens are offered as colors; no color is taken from anywhere else.
 *
 *  The photo is sent and removed the moment it is chosen, as the logo is;
 *  a stored photo is then selected, and wearing it saves with the section
 *  like any other choice. */
export default function CoverGroundField({
  slug,
  value,
  followed,
  hasPhoto,
  onChange,
  onPhotoStored,
  onPhotoRemoved,
}: {
  slug: string;
  /** The organizer's choice; null follows the logo. */
  value: CoverGround | null;
  /** What following the logo gives now, named on that option so the choice
   *  is made knowing it. */
  followed: CoverTint;
  hasPhoto: boolean;
  onChange: (value: CoverGround | null) => void;
  /** A photo was uploaded: select it, unsaved. */
  onPhotoStored: () => void;
  /** The photo was deleted on the server. */
  onPhotoRemoved: () => void;
}) {
  const { t } = useTranslation();
  const picker = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // bumped on upload so the preview re-fetches past the browser cache
  const [version, setVersion] = useState(0);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    try {
      await api.uploadCoverPhoto(slug, file);
      setVersion((v) => v + 1);
      onPhotoStored();
    } catch (err) {
      if (err instanceof ApiError && err.status === 413) {
        setError(t("setup.identity.coverPhotoTooLarge"));
      } else if (err instanceof ApiError && (err.status === 415 || err.status === 422)) {
        setError(t("setup.identity.coverPhotoUnsupportedFormat"));
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError(t("setup.identity.coverPhotoNotAuthorized"));
      } else {
        setError(
          t("setup.identity.coverPhotoUploadFailed", {
            status: err instanceof ApiError ? err.status : "?",
          }),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      // the server returns a cover that wore the photo to following the logo
      await api.deleteCoverPhoto(slug);
      onPhotoRemoved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-field qualification-control">
      <span>{t("setup.identity.coverGround")}</span>
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
      <label className="qualification-option">
        <input
          type="radio"
          name={`${slug}-cover-tint`}
          checked={value === "photo"}
          disabled={busy}
          onChange={() => {
            // a photo is worn only once there is one: without it, the choice
            // is to upload one
            if (hasPhoto) onChange("photo");
            else picker.current?.click();
          }}
        />
        {t("setup.identity.coverPhoto")}
      </label>
      <div className="cover-photo-control">
        {hasPhoto && (
          <img
            className="cover-photo-preview"
            src={`${coverPhotoUrl(slug)}?v=${version}`}
            alt={t("setup.identity.coverPhoto")}
          />
        )}
        <div className="logo-control-actions">
          <label className="logo-upload">
            {t("setup.identity.coverPhotoUpload")}
            <input
              ref={picker}
              type="file"
              accept="image/*"
              disabled={busy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
                event.target.value = "";
              }}
            />
          </label>
          {hasPhoto && (
            <button
              type="button"
              className="link-button"
              disabled={busy}
              onClick={() => void remove()}
            >
              {t("setup.identity.coverPhotoRemove")}
            </button>
          )}
        </div>
        <span className="rail-hint">{t("setup.identity.coverPhotoHint")}</span>
        {error && <span className="login-error">{error}</span>}
      </div>
    </div>
  );
}
