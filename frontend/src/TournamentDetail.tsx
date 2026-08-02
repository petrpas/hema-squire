import { IconArrowDown, IconArrowUp, IconSearch, IconX } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import HRSearchPicker from "./HRSearch";
import PaidStamp from "./PaidStamp";
import {
  type Account,
  type Availability,
  type HRProfile,
  type PaymentInstructions,
  type RegistrationDetail,
  type RosterMember,
  type TeamEntry,
  type TournamentDetail as TournamentDetailData,
  api,
} from "./api";
import { formatMoney, formatMoneyWithEur } from "./money";
import {
  DiscountList,
  DisciplinesInfo,
  InfoHeader,
  OtherActionsInfo,
  RegistrationForm,
  amendmentOpen,
  registrationStatus,
} from "./TournamentFace";

function PaymentPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [payment, setPayment] = useState<PaymentInstructions | null>(null);

  useEffect(() => {
    api.paymentInstructions(slug).then(setPayment, () => setPayment(null));
  }, [slug]);

  if (!payment) return null;

  return (
    <section className="payment-slip">
      <h2 className="payment-slip-title">{t("payment.title")}</h2>
      <img
        className="payment-qr"
        src={`data:image/png;base64,${payment.qr_png_base64}`}
        alt={t("payment.title")}
      />
      <div className="param-fields">
        <div className="param-field">
          <span>{t("payment.amount")}</span>
          <strong className="data-value">
            {formatMoney(payment.amount, payment.currency)}
          </strong>
        </div>
        <div className="param-field">
          <span>{t("payment.iban")}</span>
          <strong className="data-value">{payment.iban}</strong>
        </div>
        <div className="param-field">
          <span>{t("payment.vs")}</span>
          <strong className="data-value">{payment.vs}</strong>
        </div>
        <div className="param-field">
          <span>{t("payment.expiresAt")}</span>
          <strong>{new Date(payment.expires_at ?? "").toLocaleDateString("cs")}</strong>
        </div>
      </div>
      <p className="rail-hint">{t("payment.vsInMessage", { vs: payment.vs })}</p>

      {/* the same registration, payable in EUR against the same account */}
      {payment.eur_amount !== null && payment.eur_qr_png_base64 && (
        <>
          <h3 className="register-section">{t("payment.eurTitle")}</h3>
          <img
            className="payment-qr"
            src={`data:image/png;base64,${payment.eur_qr_png_base64}`}
            alt={t("payment.eurTitle")}
          />
          <div className="param-field">
            <span>{t("payment.eurAmount")}</span>
            <strong className="data-value">{formatMoney(payment.eur_amount, "EUR")}</strong>
          </div>
          <p className="rail-hint">{t("payment.eurHint")}</p>
        </>
      )}
    </section>
  );
}

function RegistrationStateTag({ registration }: { registration: RegistrationDetail }) {
  const { t } = useTranslation();
  const label = t(`registration.state.${registration.state}`);
  if (registration.state === "paid") return <PaidStamp id={registration.vs} label={label} />;
  if (registration.state === "reserved") return <span className="tag tag-form-yellow">{label}</span>;
  return <span className="state-text">{label}</span>;
}

/** What a registration holds and what it owes — shared by the read-only summary
 *  and the owner's panel, so the two can never disagree. */
function RegistrationLines({
  registration,
  detail,
}: {
  registration: RegistrationDetail;
  detail: TournamentDetailData;
}) {
  const { t } = useTranslation();
  const active = registration.entries.filter((e) => !e.is_substitute);
  const substitutes = registration.entries.filter((e) => e.is_substitute);

  return (
    <>
      <ul className="detail-list">
        {active.map((e) => (
          <li key={e.code}>{e.code}</li>
        ))}
        {substitutes.map((e) => (
          <li key={e.code} className="muted">
            {e.code} — {t("registration.queuePosition", { position: e.queue_position })}
          </li>
        ))}
        {registration.teams.map((team) => (
          <li key={`team-${team.id}`} className={team.waitlisted ? "muted" : undefined}>
            {team.name} — {team.code}: {formatMoneyWithEur(team.fee, team.fee_eur, detail)}
            {team.waitlisted && ` (${t("registration.teamWaitlisted")})`}
            {team.members.length > 0 && (
              <ul className="detail-list">
                {team.members.map((member, index) => (
                  <li key={index} className="muted">
                    {member.name}
                    {member.club && ` · ${member.club}`}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
        {registration.extras.map((extra) => (
          <li key={extra.extra_item_id}>
            {extra.name} × {extra.qty}
            {extra.option_value && ` (${extra.option_label}: ${extra.option_value})`}
          </li>
        ))}
      </ul>
      <p className="form-total">
        {t("form.total", {
          amount: formatMoneyWithEur(registration.total_amount, registration.total_eur, detail),
        })}
      </p>
      {(Number(registration.outstanding_amount) !== 0 ||
        Number(registration.outstanding_eur_amount ?? 0) !== 0) && (
        <p className="rail-hint">
          {t("registration.outstanding", {
            amount: formatMoneyWithEur(
              registration.outstanding_amount,
              registration.outstanding_eur_amount,
              detail,
            ),
          })}
        </p>
      )}
    </>
  );
}

/** Adds, removes, renames, rebinds, and reorders a team's roster through its
 *  own endpoint alone — no total, VS, or capacity is touched (design
 *  team-disciplines D6). Offered independently of the amendment window: it
 *  remains available after `amendments_close` and is absent only when the
 *  registration itself is cancelled or expired (spec: "Roster editing changes
 *  no money", scenario "Editor open after amendments close"). */
function RosterEditor({
  slug,
  team,
  onUpdated,
}: {
  slug: string;
  team: TeamEntry;
  onUpdated: (team: TeamEntry) => void;
}) {
  const { t } = useTranslation();
  const [members, setMembers] = useState<RosterMember[]>(() =>
    team.members.length > 0 ? team.members : team.prefill ? [team.prefill] : [],
  );
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [rebindIndex, setRebindIndex] = useState<number | null>(null);

  function patch(next: RosterMember[]) {
    setMembers(next);
    setDirty(true);
  }

  function renameMember(index: number, name: string) {
    patch(members.map((m, i) => (i === index ? { ...m, name } : m)));
  }

  function removeMember(index: number) {
    patch(members.filter((_, i) => i !== index));
  }

  function moveMember(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= members.length) return;
    const next = [...members];
    [next[index], next[target]] = [next[target], next[index]];
    patch(next);
  }

  function addTyped() {
    const name = newName.trim();
    if (!name) return;
    patch([...members, { name, hr_id: null, club: null, nationality: null }]);
    setNewName("");
  }

  function addFromSearch(profile: HRProfile) {
    patch([
      ...members,
      {
        name: profile.name,
        hr_id: profile.hr_id,
        club: profile.club,
        nationality: profile.nationality,
      },
    ]);
    setSearchOpen(false);
  }

  function rebindFromSearch(profile: HRProfile) {
    if (rebindIndex === null) return;
    patch(
      members.map((m, i) =>
        i === rebindIndex
          ? {
              name: profile.name,
              hr_id: profile.hr_id,
              club: profile.club,
              nationality: profile.nationality,
            }
          : m,
      ),
    );
    setRebindIndex(null);
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateRoster(
        slug,
        team.id,
        members.map((m) => ({
          name: m.name,
          hr_id: m.hr_id,
          club: m.club,
          nationality: m.nationality,
        })),
      );
      onUpdated(updated);
      setDirty(false);
    } catch {
      setError(t("roster.saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  const shortfall = Math.max(team.team_min - members.length, 0);

  return (
    <div className="rail-card dashed">
      <h3 className="register-section">{t("roster.title", { team: team.name })}</h3>
      <p className="rail-hint">{t("roster.bounds", { min: team.team_min, max: team.team_max })}</p>
      {shortfall > 0 && <p className="rail-hint">{t("roster.shortfall", { count: shortfall })}</p>}

      <ul className="detail-list">
        {members.map((member, index) => (
          <li key={index}>
            <div className="checklist-row team-row">
              <input
                className="cell-input"
                value={member.name}
                onChange={(event) => renameMember(index, event.target.value)}
              />
              {member.club && <span className="muted"> {member.club}</span>}
              <button
                type="button"
                className="row-action"
                title={t("roster.moveUp")}
                disabled={index === 0}
                onClick={() => moveMember(index, -1)}
              >
                <IconArrowUp size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("roster.moveDown")}
                disabled={index === members.length - 1}
                onClick={() => moveMember(index, 1)}
              >
                <IconArrowDown size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("roster.rebind")}
                onClick={() => setRebindIndex(rebindIndex === index ? null : index)}
              >
                <IconSearch size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("actions.delete")}
                onClick={() => removeMember(index)}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </div>
            {rebindIndex === index && (
              <HRSearchPicker
                lockedQuery={member.name}
                onConfirm={rebindFromSearch}
                onCancel={() => setRebindIndex(null)}
              />
            )}
          </li>
        ))}
      </ul>

      {members.length < team.team_max && (
        <>
          <div className="team-add-row">
            <input
              value={newName}
              placeholder={t("roster.namePlaceholder")}
              onChange={(event) => setNewName(event.target.value)}
            />
            <button
              type="button"
              className="secondary"
              disabled={!newName.trim()}
              onClick={addTyped}
            >
              {t("roster.add")}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setSearchOpen(!searchOpen)}
            >
              {t("roster.search")}
            </button>
          </div>
          {searchOpen && (
            <HRSearchPicker onConfirm={addFromSearch} onCancel={() => setSearchOpen(false)} />
          )}
        </>
      )}

      {error && <p className="login-error">{error}</p>}
      <button
        className="btn-primary param-save"
        disabled={busy || !dirty}
        onClick={() => void save()}
      >
        {t("roster.save")}
      </button>
    </div>
  );
}

function RegistrationSummary({
  registration,
  detail,
}: {
  registration: RegistrationDetail;
  detail: TournamentDetailData;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{t("registration.title")}</h2>
      <RegistrationStateTag registration={registration} />
      <RegistrationLines registration={registration} detail={detail} />
    </section>
  );
}

function RegistrationPanel({
  slug,
  detail,
  registration,
  canAmend,
  onAmend,
  onCancelled,
  onTeamUpdated,
}: {
  slug: string;
  detail: TournamentDetailData;
  registration: RegistrationDetail;
  canAmend: boolean;
  onAmend: () => void;
  onCancelled: () => void;
  onTeamUpdated: (team: TeamEntry) => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const active = registration.entries.filter((e) => !e.is_substitute);
  const substitutes = registration.entries.filter((e) => e.is_substitute);
  const fullyQueued = active.length === 0 && substitutes.length > 0;

  async function cancel() {
    setBusy(true);
    try {
      await api.cancelRegistration(slug);
      onCancelled();
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  const refundable =
    registration.state === "paid" &&
    detail.refundable_until !== null &&
    new Date().toISOString().slice(0, 10) <= detail.refundable_until;

  return (
    <section className="rail-card">
      <h2>{t("registration.title")}</h2>
      <RegistrationStateTag registration={registration} />

      <RegistrationLines registration={registration} detail={detail} />

      {registration.state === "reserved" && !fullyQueued && <PaymentPanel slug={slug} />}
      {registration.state === "reserved" && fullyQueued && (
        <p className="rail-hint">{t("registration.fullyQueuedHint")}</p>
      )}

      {(registration.state === "reserved" || registration.state === "paid") &&
        registration.teams.map((team) => (
          <RosterEditor key={team.id} slug={slug} team={team} onUpdated={onTeamUpdated} />
        ))}

      {canAmend && (
        <button className="secondary" onClick={onAmend}>
          {t("registration.amend")}
        </button>
      )}

      {registration.state !== "cancelled" && (
        <>
          {confirming ? (
            <div className="rail-card dashed">
              <p>
                {registration.state === "paid"
                  ? refundable
                    ? t("cancel.refundable")
                    : t("cancel.notRefundable")
                  : t("cancel.confirm")}
              </p>
              <div className="modal-actions">
                <button className="secondary" onClick={() => setConfirming(false)}>
                  {t("common.cancel")}
                </button>
                <button className="btn-primary" disabled={busy} onClick={() => void cancel()}>
                  {t("cancel.confirmButton")}
                </button>
              </div>
            </div>
          ) : (
            <button className="secondary" onClick={() => setConfirming(true)}>
              {t("cancel.button")}
            </button>
          )}
        </>
      )}
    </section>
  );
}

export default function TournamentDetail({
  slug,
  readOnly = false,
  onBack,
  onProfile,
  onAdmin,
  onOrganizer,
  onLogout,
}: {
  slug: string;
  readOnly?: boolean;
  onBack: () => void;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<TournamentDetailData | null>(null);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [registration, setRegistration] = useState<RegistrationDetail | null>(null);
  const [registrationChecked, setRegistrationChecked] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  // the detail page is split into an information screen and a separate
  // register/amend screen; information is always the landing view
  const [screen, setScreen] = useState<"information" | "register" | "amend">("information");

  function refresh() {
    api.tournament(slug).then(setDetail, () => setDetail(null));
    api.availability(slug).then(setAvailability, () => setAvailability([]));
    api.myRegistration(slug).then(
      (r) => {
        setRegistration(r);
        setRegistrationChecked(true);
      },
      () => {
        setRegistration(null);
        setRegistrationChecked(true);
      },
    );
  }

  useEffect(refresh, [slug]);
  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const hasActive = registration !== null && registration.state !== "cancelled";
  // register is offered only when open and at least one discipline or item has
  // an open slot (extra items carry no capacity, so their presence counts)
  const hasOpenSlot =
    detail !== null &&
    (availability.some((a) => a.free > 0) || detail.extra_items.length > 0);
  const canRegister =
    !readOnly &&
    !hasActive &&
    detail !== null &&
    registrationStatus(detail) === "open" &&
    hasOpenSlot;
  const canAmend =
    !readOnly &&
    detail !== null &&
    registration !== null &&
    (registration.state === "reserved" || registration.state === "paid") &&
    amendmentOpen(detail);
  const onRegisterScreen = screen === "register" && canRegister;
  const onAmendScreen = screen === "amend" && canAmend;
  const showingForm = onRegisterScreen || onAmendScreen;

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={onBack}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </div>
      <div className="login-card wide-card">
        <button
          className="link-button"
          onClick={() => (showingForm ? setScreen("information") : onBack())}
        >
          {showingForm ? t("detail.backToInfo") : t("detail.back")}
        </button>
        {detail === null || !registrationChecked ? (
          <p>{t("common.loading")}</p>
        ) : showingForm ? (
          <div className="setup-panel">
            <RegistrationForm
              detail={detail}
              availability={availability}
              mode={
                onAmendScreen && registration
                  ? {
                      kind: "amend",
                      initial: registration,
                      onRegistered: (r) => {
                        setRegistration(r);
                        setScreen("information");
                      },
                    }
                  : {
                      kind: "register",
                      onRegistered: (r) => {
                        setRegistration(r);
                        setScreen("information");
                      },
                    }
              }
            />
          </div>
        ) : (
          <div className="setup-panel">
            <InfoHeader detail={detail} />
            <DisciplinesInfo detail={detail} availability={availability} />
            <DiscountList detail={detail} />
            <OtherActionsInfo detail={detail} />
            {readOnly ? (
              hasActive && registration && (
                <RegistrationSummary registration={registration} detail={detail} />
              )
            ) : hasActive && registration ? (
              <RegistrationPanel
                slug={slug}
                detail={detail}
                registration={registration}
                canAmend={canAmend}
                onAmend={() => setScreen("amend")}
                onCancelled={refresh}
                onTeamUpdated={(updated) =>
                  setRegistration((prev) =>
                    prev
                      ? {
                          ...prev,
                          teams: prev.teams.map((team) =>
                            team.id === updated.id ? updated : team,
                          ),
                        }
                      : prev,
                  )
                }
              />
            ) : canRegister ? (
              <button className="btn-primary param-save" onClick={() => setScreen("register")}>
                {t("detail.register")}
              </button>
            ) : (
              <section className="rail-card dashed">
                <p className="rail-hint">
                  {registrationStatus(detail) === "opens_on"
                    ? t("detail.notYetOpen")
                    : t("detail.closedNotice")}
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
