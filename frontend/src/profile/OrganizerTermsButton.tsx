import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Account } from "../api";
import Modal from "../Modal";

/** The organizer data terms the account accepted or owes, kept out of the
 *  way: a button below the Privacy tab's sections, opening the text with the
 *  version and date it was accepted (spec `profile-page`, The Profile page has
 *  a Privacy tab). Only for read; accepting happens at the console. */
export default function OrganizerTermsButton({ account }: { account: Account }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const acceptedAt = account.organizer_terms_accepted_at;
  if (acceptedAt === null && !account.organizer_terms_due) return null;
  const paragraphs = t("privacy.terms.paragraphs", { returnObjects: true }) as string[];

  return (
    <>
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        {t("privacy.terms.title")}
      </button>
      {open && (
        <Modal onClose={() => setOpen(false)}>
          <div className="modal">
            <h2>{t("privacy.terms.title")}</h2>
            <p className="rail-hint">
              {acceptedAt !== null
                ? t("profile.privacy.termsAccepted", {
                    version: account.organizer_terms_version ?? "",
                    date: new Date(acceptedAt).toLocaleDateString(account.language),
                  })
                : t("profile.privacy.termsDue")}
            </p>
            {paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setOpen(false)}>
                {t("common.close")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
