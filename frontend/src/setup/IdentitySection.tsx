import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api, logoUrl } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString, type FieldError as FieldErrorValue } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

// Identity fields patched as a whole, mirroring ParamPanel's save pattern
// but for the fields that live in the Setup tab's main content, not the rail.
const IDENTITY_FIELDS = [
  { key: "display_name", type: "text" },
  { key: "subtitle", type: "text" },
  { key: "date", type: "date" },
  // one line, so the inline markdown subset only — links and emphasis
  { key: "location", type: "text", inlineMarkdown: true },
  { key: "description", type: "textarea", markdown: true },
  // shown only on the registration form, unlike description
  {
    key: "registration_instructions",
    type: "textarea",
    hint: "setup.identity.registrationInstructionsHint",
    markdown: true,
  },
] as const;

// rendered as three runs — [display_name, subtitle], [date, location, description],
// [registration_instructions] — with the logo block after the first and the
// qualification block after the second, so the section reads name, subtitle,
// logo, date, location, description, qualification, reg. instructions (design
// D5). The registration window moved to TIMELINE (regroup-setup-parameters);
// the tournament's own date stays here, its only editor.
const IDENTITY_RUN_1 = IDENTITY_FIELDS.slice(0, 2);
const IDENTITY_RUN_2 = IDENTITY_FIELDS.slice(2, 5);
const IDENTITY_RUN_3 = IDENTITY_FIELDS.slice(5);

// text/textarea IDENTITY_FIELDS checked against TournamentUpdate's bounds
// (dates are excluded — the browser's own date input is already typed)
const IDENTITY_TEXT_CHECKS: Record<string, (value: string) => FieldErrorValue | null> = {
  display_name: (value) => checkString("display_name", "TournamentUpdate.display_name", value, { required: true }),
  subtitle: (value) => checkString("subtitle", "TournamentUpdate.subtitle", value),
  location: (value) => checkString("location", "TournamentUpdate.location", value),
  description: (value) => checkString("description", "TournamentUpdate.description", value, { multiline: true }),
  registration_instructions: (value) =>
    checkString(
      "registration_instructions",
      "TournamentUpdate.registration_instructions",
      value,
      { multiline: true },
    ),
};

export function IdentitySection({
  detail,
  slug,
  onSaved,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [qualificationOpen, setQualificationOpen] = useState(true);
  const [qualificationCriteria, setQualificationCriteria] = useState("");
  const [dirty, setDirty] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  // bumped on upload/remove so the <img> re-fetches past the browser cache
  const [logoVersion, setLogoVersion] = useState(0);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | HTMLTextAreaElement | null>>({});

  function qualificationCriteriaCheck(): FieldErrorValue | null {
    if (!qualificationOpen && qualificationCriteria.trim() === "") {
      return { field: "qualification_criteria", code: "qualification_criteria_required", params: {} };
    }
    return checkString(
      "qualification_criteria",
      "TournamentUpdate.qualification_criteria",
      qualificationCriteria,
      { multiline: true },
    );
  }

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

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const field of IDENTITY_FIELDS) {
      const value = detail[field.key];
      next[field.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(next);
    setQualificationOpen(detail.qualification_open);
    setQualificationCriteria(detail.qualification_criteria ?? "");
    validation.clearAll();
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  useSectionSaver(registry, "tournament", "identity", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () =>
      validation.validateAll([
        ...Object.entries(IDENTITY_TEXT_CHECKS).map(
          ([key, check]) => () => check(values[key] ?? ""),
        ),
        qualificationCriteriaCheck,
      ]),
    focusFirstInvalid: () => {
      for (const [key, check] of Object.entries(IDENTITY_TEXT_CHECKS)) {
        if (check(values[key] ?? "")) {
          fieldRefs.current[key]?.focus();
          return;
        }
      }
      if (qualificationCriteriaCheck()) fieldRefs.current.qualification_criteria?.focus();
    },
    flush: async () => {
      try {
        const patch: Record<string, unknown> = {};
        for (const field of IDENTITY_FIELDS) {
          const raw = values[field.key] ?? "";
          patch[field.key] = raw === "" ? null : raw;
        }
        patch.qualification_open = qualificationOpen;
        patch.qualification_criteria = qualificationOpen ? null : qualificationCriteria || null;
        await api.updateTournament(slug, patch);
        setDirty(false);
        return [{ change: "identity", section: "identity", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        return [{ change: "identity", section: "identity", error: message }];
      }
    },
  });

  function renderField(field: (typeof IDENTITY_FIELDS)[number]) {
    const check = IDENTITY_TEXT_CHECKS[field.key];
    const error = validation.errors[field.key];
    return field.type === "textarea" ? (
      <label key={field.key} className="form-field">
        <span>
          {t(`param.${field.key}`)}
          {"hint" in field && <HelpHint text={t(field.hint)} />}
        </span>
        <textarea
          ref={(el) => {
            fieldRefs.current[field.key] = el;
          }}
          className={"markdown" in field && field.markdown ? "markdown-input" : undefined}
          value={values[field.key] ?? ""}
          onChange={(event) => {
            setValues({ ...values, [field.key]: event.target.value });
            setDirty(true);
            if (check) validation.clearIfValid(field.key, () => check(event.target.value));
          }}
          onBlur={(event) => {
            if (check) validation.touch(field.key, () => check(event.target.value));
          }}
          {...invalidProps(field.key, error)}
        />
        {"markdown" in field && field.markdown && (
          <span className="markdown-hint">{t("setup.identity.markdownHint")}</span>
        )}
        <FieldError field={field.key} error={error} />
      </label>
    ) : (
      <label key={field.key} className="form-field">
        <span>{t(`param.${field.key}`)}</span>
        <input
          ref={(el) => {
            fieldRefs.current[field.key] = el;
          }}
          type={field.type}
          value={values[field.key] ?? ""}
          onChange={(event) => {
            setValues({ ...values, [field.key]: event.target.value });
            setDirty(true);
            if (check) validation.clearIfValid(field.key, () => check(event.target.value));
          }}
          onBlur={(event) => {
            if (check) validation.touch(field.key, () => check(event.target.value));
          }}
          {...invalidProps(field.key, error)}
        />
        {"inlineMarkdown" in field && field.inlineMarkdown && (
          <span className="markdown-hint">{t("setup.inlineMarkdownHint")}</span>
        )}
        <FieldError field={field.key} error={error} />
      </label>
    );
  }

  return (
    <section className="rail-card">
      <div className="form-fields">{IDENTITY_RUN_1.map(renderField)}</div>
      <div className="logo-control">
        <span className="logo-control-label">{t("setup.identity.logo")}</span>
        {detail.has_logo && (
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
          {detail.has_logo && (
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
      <div className="form-fields">{IDENTITY_RUN_2.map(renderField)}</div>
      <div className="form-field qualification-control">
        <span>{t("setup.identity.qualification")}</span>
        <label className="qualification-option">
          <input
            type="radio"
            name={`${slug}-qualification`}
            checked={qualificationOpen}
            onChange={() => {
              setQualificationOpen(true);
              setDirty(true);
            }}
          />
          {t("setup.identity.qualificationOpen")}
        </label>
        <label className="qualification-option">
          <input
            type="radio"
            name={`${slug}-qualification`}
            checked={!qualificationOpen}
            onChange={() => {
              setQualificationOpen(false);
              setDirty(true);
            }}
          />
          {t("setup.identity.qualificationRequired")}
        </label>
        {!qualificationOpen && (
          <label className="form-field">
            <span>
              {t("setup.identity.qualificationCriteria")}
              <HelpHint text={t("setup.identity.qualificationCriteriaHint")} />
            </span>
            <input
              ref={(el) => {
                fieldRefs.current.qualification_criteria = el;
              }}
              value={qualificationCriteria}
              onChange={(event) => {
                setQualificationCriteria(event.target.value);
                setDirty(true);
                validation.clearIfValid("qualification_criteria", qualificationCriteriaCheck);
              }}
              onBlur={() => validation.touch("qualification_criteria", qualificationCriteriaCheck)}
              {...invalidProps("qualification_criteria", validation.errors.qualification_criteria)}
            />
            <FieldError
              field="qualification_criteria"
              error={validation.errors.qualification_criteria}
            />
          </label>
        )}
      </div>
      <div className="form-fields">{IDENTITY_RUN_3.map(renderField)}</div>
    </section>
  );
}

export function VsSeriesSection({ detail }: { detail: TournamentDetail }) {
  const { t } = useTranslation();

  return (
    <section className="rail-card">
      <h2>{t("setup.vsSeries.title")}</h2>
      <p className="rail-hint">{t("setup.vsSeries.prefix", { prefix: detail.vs_prefix })}</p>
    </section>
  );
}
