import { useState } from "react";
import { useTranslation } from "react-i18next";

import HRSearchPicker from "./HRSearch";
import { type HRProfile, type RosterMember } from "./api";

/** Names one roster member, in one place: the name is typed once, the HEMA
 *  Ratings search runs on that same name, and confirming either a result or
 *  the typed name alone yields the member (spec: "Member added through the
 *  dialog"). An unbound member — a name the search does not know — is a
 *  complete member, so confirming the typed name is a first-class outcome and
 *  not a fallback.
 *
 *  Used both to add a member and to rebind an existing one; the caller seeds
 *  `initial` for the latter. */
export default function RosterMemberDialog({
  initial,
  onConfirm,
  onClose,
}: {
  /** The member being rebound, or null when adding a new one. */
  initial: RosterMember | null;
  onConfirm: (member: RosterMember) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial?.name ?? "");
  const [searching, setSearching] = useState(false);

  const trimmed = name.trim();

  function confirmProfile(profile: HRProfile) {
    onConfirm({
      name: profile.name,
      hr_id: profile.hr_id,
      club: profile.club,
      nationality: profile.nationality,
    });
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t(initial ? "roster.rebindTitle" : "roster.addTitle")}</h2>
        <div className="form-fields">
          <label className="form-field">
            <span>{t("roster.namePlaceholder")}</span>
            <input
              autoFocus
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setSearching(false);
              }}
            />
          </label>
        </div>
        <p className="rail-hint">{t("roster.searchHint")}</p>

        {searching ? (
          // the picker searches the name typed above rather than asking for it
          // again — one name field on screen at any moment
          <HRSearchPicker lockedQuery={trimmed} onConfirm={confirmProfile} />
        ) : (
          <button
            type="button"
            className="secondary"
            disabled={trimmed.length < 3}
            onClick={() => setSearching(true)}
          >
            {t("roster.search")}
          </button>
        )}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={trimmed === ""}
            onClick={() =>
              onConfirm({
                name: trimmed,
                hr_id: null,
                club: null,
                nationality: null,
              })
            }
          >
            {t("roster.confirmPlain")}
          </button>
        </div>
      </div>
    </div>
  );
}
