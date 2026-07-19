import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HRProfile, api } from "./api";

/** Search-by-name HR candidate picker, shared by the Profile page's HR
 * binding and the signup window's optional HR step. The caller decides what
 * "confirming" a candidate means (bind immediately vs. stage for signup). */
export default function HRSearchPicker({
  onConfirm,
  busy: externalBusy,
}: {
  onConfirm: (profile: HRProfile) => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();
  const [nationalities, setNationalities] = useState<string[]>([]);
  const [nationality, setNationality] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<HRProfile[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.hrNationalities().then(setNationalities, () => setNationalities([]));
  }, []);

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
            <option value="">{t("profile.hr.anyNationality")}</option>
            {nationalities.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="param-field">
          <span>{t("match.placeholder")}</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void search();
              }
            }}
          />
        </label>
      </div>
      <button
        type="button"
        className="secondary"
        onClick={() => void search()}
        disabled={disabled || query.trim().length < 3}
      >
        {t("profile.hr.search")}
      </button>
      {results && (
        <ul className="match-results">
          {results.map((profile) => (
            <li key={profile.hr_id}>
              <button type="button" onClick={() => onConfirm(profile)} disabled={disabled}>
                <strong>{profile.name}</strong>
                <span className="muted">
                  {profile.club ?? "—"} · {profile.nationality ?? "—"} · #{profile.hr_id}
                </span>
              </button>
            </li>
          ))}
          {results.length === 0 && <li className="muted match-empty">{t("match.noResults")}</li>}
        </ul>
      )}
    </>
  );
}
