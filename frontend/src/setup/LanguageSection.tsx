import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type TournamentDetail } from "../api";
import HelpHint from "../HelpHint";
import i18n from "../i18n";

const IMPLEMENTED_LANGUAGES = Object.keys(i18n.options.resources ?? {});

/** The tournament's communication language: what mail falls back to for a
 *  fencer whose own language Squire does not know (spec localization).
 *
 *  Applies at once, like the rest of `OTHER`: the tab has no save control, and
 *  a section there carries its own action (spec setup-navigation). */
export function LanguageSection({
  slug,
  detail,
  onApplied,
}: {
  slug: string;
  detail: TournamentDetail;
  /** Refetches the tournament so the select reads the stored value. */
  onApplied: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function apply(language: string) {
    setBusy(true);
    setFailed(false);
    try {
      await api.updateTournament(slug, { language });
      onApplied();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>
        {t("setup.language.title")}
        <HelpHint text={t("setup.language.hint")} />
      </h2>
      <label className="param-field">
        <span>{t("setup.language.label")}</span>
        <select
          value={detail.language}
          disabled={busy}
          onChange={(event) => void apply(event.target.value)}
        >
          {IMPLEMENTED_LANGUAGES.map((code) => (
            <option key={code} value={code}>
              {t(`languages.${code}`)}
            </option>
          ))}
        </select>
      </label>
      {failed && <p className="login-error">{t("setup.language.failed")}</p>}
    </section>
  );
}
