import { IconArrowDown, IconArrowUp, IconSearch, IconX } from "@tabler/icons-react";
import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import NotFound from "./NotFound";
import PaidStamp from "./PaidStamp";
import RosterMemberDialog from "./RosterMemberDialog";
import { type HomeTab } from "./FencerShell";
import { home } from "./routes";
import {
  type Availability,
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
/** One line of a registration: what it is, and what it costs, the amount
 *  sitting in the shared right-hand column. */
function AmountLine({
  label,
  amount,
  className,
  children,
}: {
  label: ReactNode;
  amount?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div className={className ? `amount-line ${className}` : "amount-line"}>
      <span className="amount-label">{label}</span>
      <span className="amount-value">{amount}</span>
      {children && <div className="amount-detail">{children}</div>}
    </div>
  );
}

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
  // discipline entries are identified by slug, but a fencer never reads a
  // slug (design discipline-identity D6) — the name is what tells them which
  // one they entered
  const discipline = new Map(detail.disciplines.map((d) => [d.slug, d]));
  const item = new Map(detail.extra_items.map((x) => [x.id, x]));

  /** A discipline's own fee, stated as the tournament lists it — the
   *  registration's total below is the server's, discounts and all. */
  function disciplineFee(slug: string) {
    const d = discipline.get(slug);
    if (!d || d.fee === null) return null;
    return formatMoneyWithEur(d.fee, d.fee_eur, detail);
  }

  return (
    <div className="registration-lines">
      {active.map((e) => (
        <AmountLine
          key={e.slug}
          label={discipline.get(e.slug)?.name ?? e.slug}
          amount={disciplineFee(e.slug)}
        />
      ))}
      {substitutes.map((e) => (
        <AmountLine
          key={e.slug}
          className="muted"
          label={`${discipline.get(e.slug)?.name ?? e.slug} — ${t("registration.queuePosition", {
            position: e.queue_position,
          })}`}
          amount={disciplineFee(e.slug)}
        />
      ))}
      {registration.teams.map((team) => (
        <AmountLine
          key={`team-${team.id}`}
          className={team.waitlisted ? "muted" : undefined}
          // the discipline names the entry, the team names the entrant
          label={`${discipline.get(team.slug)?.name ?? team.slug}: ${team.name}${
            team.waitlisted ? ` (${t("registration.teamWaitlisted")})` : ""
          }`}
          amount={formatMoneyWithEur(team.fee, team.fee_eur, detail)}
        >
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
        </AmountLine>
      ))}
      {registration.extras.map((extra) => {
        const priced = item.get(extra.extra_item_id);
        return (
          <AmountLine
            key={extra.extra_item_id}
            label={`${extra.name} × ${extra.qty}${
              extra.option_value ? ` (${extra.option_label}: ${extra.option_value})` : ""
            }`}
            amount={
              priced
                ? formatMoneyWithEur(
                    priced.price * extra.qty,
                    priced.price_eur === null ? null : priced.price_eur * extra.qty,
                    detail,
                  )
                : null
            }
          />
        );
      })}
      <AmountLine
        className="amount-total"
        label={t("form.totalLabel")}
        amount={formatMoneyWithEur(registration.total_amount, registration.total_eur, detail)}
      />
      {(Number(registration.outstanding_amount) !== 0 ||
        Number(registration.outstanding_eur_amount ?? 0) !== 0) && (
        <AmountLine
          className="muted"
          label={t("registration.outstandingLabel")}
          amount={formatMoneyWithEur(
            registration.outstanding_amount,
            registration.outstanding_eur_amount,
            detail,
          )}
        />
      )}
    </div>
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
  // one slot: naming a member happens in the dialog, whether the member is
  // being added or rebound, so the roster itself carries no name field and no
  // search block (spec: "Member added through the dialog")
  const [dialog, setDialog] = useState<{ index: number | null } | null>(null);

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

  function confirmDialog(member: RosterMember) {
    const index = dialog?.index ?? null;
    patch(index === null ? [...members, member] : members.map((m, i) => (i === index ? member : m)));
    setDialog(null);
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

      {/* one line per member: their name, their club, their row actions */}
      <ul className="detail-list">
        {members.map((member, index) => (
          <li key={index}>
            <div className="checklist-row team-row">
              <input
                className="cell-input"
                value={member.name}
                onChange={(event) => renameMember(index, event.target.value)}
              />
              {member.club && <span className="muted">{member.club}</span>}
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
                onClick={() => setDialog({ index })}
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
          </li>
        ))}
      </ul>

      {members.length < team.team_max && (
        <button type="button" className="secondary" onClick={() => setDialog({ index: null })}>
          {t("roster.add")}
        </button>
      )}

      {error && <p className="login-error">{error}</p>}
      <button
        className="btn-primary param-save"
        disabled={busy || !dirty}
        onClick={() => void save()}
      >
        {t("roster.save")}
      </button>

      {dialog && (
        <RosterMemberDialog
          initial={dialog.index === null ? null : members[dialog.index]}
          onConfirm={confirmDialog}
          onClose={() => setDialog(null)}
        />
      )}
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
  // which destructive action is awaiting its confirmation, if any — the two
  // share one slot, so neither can be confirmed behind the other
  const [confirming, setConfirming] = useState<"amend" | "cancel" | null>(null);
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
      setConfirming(null);
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

      {/* amend and cancel both rewrite something the fencer already holds, so
          both are destructive controls behind a confirmation, standing as one
          centered pair (spec design-system: "Destructive actions") */}
      {confirming !== null ? (
        <div className="rail-card dashed">
          <p>
            {confirming === "amend"
              ? t("registration.amendConfirm")
              : registration.state === "paid"
                ? refundable
                  ? t("cancel.refundable")
                  : t("cancel.notRefundable")
                : t("cancel.confirm")}
          </p>
          <div className="modal-actions">
            <button className="secondary" onClick={() => setConfirming(null)}>
              {t("common.cancel")}
            </button>
            <button
              className="btn-danger"
              disabled={busy}
              onClick={() => {
                if (confirming === "amend") {
                  setConfirming(null);
                  onAmend();
                } else {
                  void cancel();
                }
              }}
            >
              {confirming === "amend"
                ? t("registration.amendConfirmButton")
                : t("cancel.confirmButton")}
            </button>
          </div>
        </div>
      ) : (
        (canAmend || registration.state !== "cancelled") && (
          <div className="action-pair">
            {canAmend && (
              <button className="btn-danger" onClick={() => setConfirming("amend")}>
                {t("registration.amend")}
              </button>
            )}
            {registration.state !== "cancelled" && (
              <button className="btn-danger" onClick={() => setConfirming("cancel")}>
                {t("cancel.button")}
              </button>
            )}
          </div>
        )
      )}
    </section>
  );
}

export default function TournamentDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { slug = "" } = useParams();
  const [detail, setDetail] = useState<TournamentDetailData | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [registration, setRegistration] = useState<RegistrationDetail | null>(null);
  const [registrationChecked, setRegistrationChecked] = useState(false);
  // the page opens on `tournament` from every entry point (design D3); the
  // second tab, when offered, carries either the registration form or the
  // held registration, with an amendment opening in place of the latter
  const [tab, setTab] = useState<"tournament" | "registration">("tournament");
  const [amending, setAmending] = useState(false);

  function refresh() {
    api.tournament(slug).then(setDetail, () => setNotFound(true));
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

  // the close control returns to the list the page was opened from (the tab
  // carried in the Link's navigation state), or to Fencer Home's default
  // Open tab when the page was reached by URL rather than from a list
  function close() {
    const openedFrom = (location.state as { tab?: HomeTab } | null)?.tab;
    navigate(home(openedFrom));
  }

  const readOnly = detail !== null && detail.date < new Date().toISOString().slice(0, 10);
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
  const secondTabOffered = hasActive || canRegister;

  // a cancellation on a closed tournament can drop both `hasActive` and
  // `canRegister` at once — fall back before a selected-but-absent tab (or a
  // stale in-progress amendment) can be reached (design D3, task 4.4)
  useEffect(() => {
    if (!secondTabOffered) {
      setTab("tournament");
      setAmending(false);
    }
  }, [secondTabOffered]);

  /** Leaving the registration tab abandons any amendment in progress — the
   *  page introduces no separate cancel control for it (design D3). */
  function selectTab(next: "tournament" | "registration") {
    if (next !== "registration") setAmending(false);
    setTab(next);
  }

  if (notFound) return <NotFound />;

  return (
    <div className="workspace detail-workspace">
      {/* the tournament's own row, under the heading the list page shares
          with this one (spec: "Tournament detail shares the home heading") */}
      <div className="detail-header">
        <h1>{detail?.display_name}</h1>
        <nav className="stage-control detail-tabs">
          <button
            className={tab === "tournament" ? "active" : ""}
            onClick={() => selectTab("tournament")}
          >
            {t("detail.tabs.tournament")}
          </button>
          {secondTabOffered && (
            <button
              className={tab === "registration" ? "active" : ""}
              onClick={() => selectTab("registration")}
            >
              {hasActive ? t("detail.tabs.registered") : t("detail.tabs.register")}
            </button>
          )}
        </nav>
        <button
          type="button"
          className="row-action"
          title={t("detail.close")}
          aria-label={t("detail.close")}
          onClick={close}
        >
          <IconX size={18} stroke={1.5} />
        </button>
      </div>
      {detail === null || !registrationChecked ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="page-card-body">
          {tab === "tournament" ? (
            <>
              <InfoHeader detail={detail} />
              <DisciplinesInfo detail={detail} availability={availability} />
              <DiscountList detail={detail} />
              <OtherActionsInfo detail={detail} />
              {!readOnly && !secondTabOffered && (
                <section className="rail-card dashed">
                  <p className="rail-hint">
                    {registrationStatus(detail) === "opens_on"
                      ? t("detail.notYetOpen")
                      : t("detail.closedNotice")}
                  </p>
                </section>
              )}
            </>
          ) : amending && registration ? (
            <RegistrationForm
              detail={detail}
              availability={availability}
              mode={{
                kind: "amend",
                initial: registration,
                onRegistered: (r) => {
                  setRegistration(r);
                  setAmending(false);
                  setTab("registration");
                },
              }}
            />
          ) : hasActive && registration ? (
            readOnly ? (
              <RegistrationSummary registration={registration} detail={detail} />
            ) : (
              <RegistrationPanel
                slug={slug}
                detail={detail}
                registration={registration}
                canAmend={canAmend}
                onAmend={() => setAmending(true)}
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
            )
          ) : (
            <RegistrationForm
              detail={detail}
              availability={availability}
              mode={{
                kind: "register",
                onRegistered: (r) => {
                  setRegistration(r);
                  setTab("registration");
                },
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
