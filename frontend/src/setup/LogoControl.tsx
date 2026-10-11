import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, logoUrl } from "../api";

/** The tournament's logo in Setup: a preview, upload and removal. Saved on its
 *  own, apart from the identity section's save bar — a file is sent the
 *  moment it is chosen. */
export default function LogoControl({
  slug,
  hasLogo,
  onSaved,
}: {
  slug: string;
  hasLogo: boolean;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  // bumped on upload/remove so the <img> re-fetches past the browser cache
  const [logoVersion, setLogoVersion] = useState(0);

  async function uploadLogo(file: File) {
    setLogoBusy(true);
    setLogoError(null);
    try {
      await api.uploadLogo(slug, file);
      setLogoVersion((v) => v + 1);
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.status === 413) {
        setLogoError(t("setup.identity.logoTooLarge"));
      } else if (err instanceof ApiError && (err.status === 415 || err.status === 422)) {
        setLogoError(t("setup.identity.logoUnsupportedFormat"));
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setLogoError(t("setup.identity.logoNotAuthorized"));
      } else if (err instanceof ApiError) {
        setLogoError(t("setup.identity.logoUploadFailed", { status: err.status }));
      } else {
        setLogoError(t("setup.identity.logoUploadFailed", { status: "?" }));
      }
    } finally {
      setLogoBusy(false);
    }
  }

  async function removeLogo() {
    setLogoBusy(true);
    setLogoError(null);
    try {
      await api.deleteLogo(slug);
      setLogoVersion((v) => v + 1);
      onSaved();
    } finally {
      setLogoBusy(false);
    }
  }

  return (
    <div className="logo-control">
      <span className="logo-control-label">{t("setup.identity.logo")}</span>
      {hasLogo && (
        <img
          className="logo-preview"
          src={`${logoUrl(slug)}?v=${logoVersion}`}
          alt={t("setup.identity.logo")}
        />
      )}
      <div className="logo-control-actions">
        <label className="logo-upload">
          {t("setup.identity.logoUpload")}
          <input
            type="file"
            accept="image/*"
            disabled={logoBusy}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void uploadLogo(file);
              event.target.value = "";
            }}
          />
        </label>
        {hasLogo && (
          <button
            type="button"
            className="link-button"
            disabled={logoBusy}
            onClick={() => void removeLogo()}
          >
            {t("setup.identity.logoRemove")}
          </button>
        )}
      </div>
      <span className="rail-hint">{t("setup.identity.logoHint")}</span>
      {logoError && <span className="login-error">{logoError}</span>}
    </div>
  );
}
