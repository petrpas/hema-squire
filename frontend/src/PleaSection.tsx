import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type Plea, api } from "./api";

export default function PleaSection({
  plea,
  onPleaChange,
}: {
  plea: Plea;
  onPleaChange: (plea: Plea) => void;
}) {
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      const result = await api.submitPlea(message.trim() === "" ? null : message.trim());
      onPleaChange(result);
      setShowForm(false);
      setMessage("");
    } finally {
      setBusy(false);
    }
  }

  if (plea.state === "pending") {
    return <p className="plea-status">{t("picker.pleaPending")}</p>;
  }

  if (showForm) {
    return (
      <div className="plea-form">
        <textarea
          value={message}
          placeholder={t("picker.pleaMessagePlaceholder")}
          onChange={(event) => setMessage(event.target.value)}
        />
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => setShowForm(false)}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void submit()}>
            {t("picker.pleaSubmit")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {plea.state === "denied" && <p className="plea-status">{t("picker.pleaDenied")}</p>}
      <button className="secondary" onClick={() => setShowForm(true)}>
        {t("picker.requestOrganizer")}
      </button>
    </div>
  );
}
