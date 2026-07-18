import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HRProfile, type SheetRow, api } from "./api";

export default function MatchDialog({
  row,
  onResolve,
  onClose,
}: {
  row: SheetRow;
  onResolve: (hrId: number | null, profile?: HRProfile) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(row.name);
  const [results, setResults] = useState<HRProfile[]>([]);

  useEffect(() => {
    const handle = setTimeout(() => {
      if (query.trim().length >= 3) {
        api.hrSearch(query).then(setResults, () => setResults([]));
      } else {
        setResults([]);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>
          {t("match.title")} — {row.name}
        </h2>
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("match.placeholder")}
        />
        <ul className="match-results">
          {results.map((profile) => (
            <li key={profile.hr_id}>
              <button onClick={() => onResolve(profile.hr_id, profile)}>
                <strong>{profile.name}</strong>
                <span className="muted">
                  {profile.nationality ?? "—"} · {profile.club ?? "—"} · #{profile.hr_id}
                </span>
              </button>
            </li>
          ))}
          {results.length === 0 && query.trim().length >= 3 && (
            <li className="muted match-empty">{t("match.noResults")}</li>
          )}
        </ul>
        <div className="modal-actions">
          <button className="link-button" onClick={() => onResolve(null)}>
            {t("match.notFound")}
          </button>
          <button className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
