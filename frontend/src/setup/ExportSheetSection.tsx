import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkUrl, type FieldError as FieldErrorValue } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

/** Where the sheet export writes. Tool configuration rather than a decision
 *  about the tournament, but it is not an operation parameter either, so it
 *  sits with the console-team and danger-zone sections it most resembles
 *  (design regroup-setup-parameters Decision 8). */
export function ExportSheetSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const fieldRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setValue(detail.output_sheet_url ?? "");
    validation.clearAll();
    setError(null);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  function check(): FieldErrorValue | null {
    return checkUrl("output_sheet_url", "TournamentUpdate.output_sheet_url", value);
  }

  useSectionSaver(registry, "other", "exportSheet", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () => validation.validateAll([check]),
    focusFirstInvalid: () => {
      if (check()) fieldRef.current?.focus();
    },
    flush: async () => {
      try {
        await api.updateTournament(slug, { output_sheet_url: value === "" ? null : value });
        setDirty(false);
        return [{ change: "exportSheet", section: "exportSheet", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setError(message);
        return [{ change: "exportSheet", section: "exportSheet", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.exportSheet.title")}</h2>
      <div className="form-fields">
        <label className="form-field">
          <span>
            {t("param.output_sheet_url")}
            <HelpHint text={t("setup.exportSheet.hint")} />
          </span>
          <input
            ref={fieldRef}
            type="text"
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setDirty(true);
              validation.clearIfValid("output_sheet_url", check);
            }}
            onBlur={() => validation.touch("output_sheet_url", check)}
            {...invalidProps("output_sheet_url", validation.errors.output_sheet_url)}
          />
          <FieldError field="output_sheet_url" error={validation.errors.output_sheet_url} />
        </label>
      </div>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
