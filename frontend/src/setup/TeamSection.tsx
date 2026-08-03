import { IconX } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TeamMember, api } from "../api";

export function TeamSection({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [team, setTeam] = useState<TeamMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [transferEmail, setTransferEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refreshTeam() {
    api.team(slug).then(setTeam, () => setTeam([]));
  }

  useEffect(refreshTeam, [slug]);

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await api.addTeamMember(slug, email.trim());
      setEmail("");
      refreshTeam();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? t("setup.team.unknownEmail")
          : err instanceof ApiError && err.status === 409
            ? t("setup.team.alreadyMember")
            : t("setup.team.addFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(fencerId: number) {
    setBusy(true);
    try {
      await api.removeTeamMember(slug, fencerId);
      refreshTeam();
    } finally {
      setBusy(false);
    }
  }

  async function transfer() {
    setBusy(true);
    setError(null);
    try {
      await api.transferOwnership(slug, transferEmail.trim());
      setTransferEmail("");
      refreshTeam();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("setup.team.transferNotMember")
          : err instanceof ApiError && err.status === 404
            ? t("setup.team.unknownEmail")
            : t("setup.team.transferFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.team.title")}</h2>
      {error && <p className="login-error">{error}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.team.email")}</th>
            <th>{t("setup.team.displayName")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {(team ?? []).map((member) => (
            <tr key={member.fencer_id}>
              <td>{member.email}</td>
              <td>{member.display_name}</td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  disabled={busy}
                  onClick={() => void remove(member.fencer_id)}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="rail-hint">{t("setup.team.addPlaceholder")}</p>
      <div className="inline-form">
        <input
          type="email"
          value={email}
          placeholder={t("setup.team.addPlaceholder")}
          onChange={(event) => setEmail(event.target.value)}
        />
        <button className="secondary" disabled={busy || !email} onClick={() => void add()}>
          {t("setup.team.add")}
        </button>
      </div>
      <p className="rail-hint">{t("setup.team.transferHint")}</p>
      <div className="inline-form">
        <input
          type="email"
          value={transferEmail}
          placeholder={t("setup.team.transferPlaceholder")}
          onChange={(event) => setTransferEmail(event.target.value)}
        />
        <button
          className="secondary"
          disabled={busy || !transferEmail}
          onClick={() => void transfer()}
        >
          {t("setup.team.transfer")}
        </button>
      </div>
    </section>
  );
}
