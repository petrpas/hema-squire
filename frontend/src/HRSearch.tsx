import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HRProfile, api } from "./api";

/** Search-by-name HR candidate picker, shared by the Profile page's HR
 * binding and the signup window's optional HR step. The caller decides what
 * "confirming" a candidate means (bind immediately vs. stage for signup). */
export default function HRSearchPicker({
  onConfirm,
  onCancel,
  busy: externalBusy,
  initialQuery = "",
  lockedQuery,
  requireNationality = false,
}: {
  onConfirm: (profile: HRProfile) => void;
  onCancel?: () => void;
  busy?: boolean;
  initialQuery?: string;
  // when set, the picker searches by this externally-owned string and hides its
  // own query input (signup reuses the form's name field — no second name line)
  lockedQuery?: string;
  requireNationality?: boolean;
}) {
  const { t } = useTranslation();
  const [nationalities, setNationalities] = useState<string[]>([]);
  const [nationality, setNationality] = useState("");
  const [internalQuery, setInternalQuery] = useState(initialQuery);
  const [results, setResults] = useState<HRProfile[] | null>(null);
  const [busy, setBusy] = useState(false);

  const locked = lockedQuery !== undefined;
  const query = locked ? lockedQuery : internalQuery;

  useEffect(() => {
    api.hrNationalities().then(setNationalities, () => setNationalities([]));
  }, []);

  useEffect(() => {
    if (!requireNationality || nationality !== "" || nationalities.length === 0) return;
    const czech = nationalities.find((n) => /^cz/i.test(n));
    setNationality(czech ?? nationalities[0]);
  }, [requireNationality, nationality, nationalities]);

  async function search() {
    setBusy(true);
    try {
      const hits = await api.hrSearch(query, nationality || null);
      setResults(hits);
    } finally {
      setBusy(false);
    }
  }

  const disabled = busy || !!externalBusy;

  return (
    <>
      <div className="param-fields">
        <label className="param-field">
          <span>{t("profile.hr.nationality")}</span>
          <select value={nationality} onChange={(event) => setNationality(event.target.value)}>
            {!requireNationality && <option value="">{t("profile.hr.anyNationality")}</option>}
            {nationalities.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        {!locked && (
          <label className="param-field">
            <span>{t("match.placeholder")}</span>
            <input
              value={internalQuery}
              onChange={(event) => setInternalQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void search();
                }
              }}
            />
          </label>
        )}
      </div>
      {onCancel ? (
        <div className="hr-search-actions">
          <button
            type="button"
            className="secondary"
            onClick={() => void search()}
            disabled={disabled || query.trim().length < 3}
          >
            {t("profile.hr.search")}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            {t("common.cancel")}
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="secondary"
          onClick={() => void search()}
          disabled={disabled || query.trim().length < 3}
        >
          {t("profile.hr.search")}
        </button>
      )}
      {results && (
        <ul className="match-results">
          {results.map((profile) => (
            <li key={profile.hr_id}>
              <button type="button" onClick={() => onConfirm(profile)} disabled={disabled}>
                <strong>{profile.name}</strong>
                <span className="muted">
                  {profile.club ?? "—"} · {profile.nationality ?? "—"} · #{profile.hr_id}
                </span>
                {profile.claimed && (
                  <span className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</span>
                )}
              </button>
            </li>
          ))}
          {results.length === 0 && <li className="muted match-empty">{t("match.noResults")}</li>}
        </ul>
      )}
    </>
  );
}
