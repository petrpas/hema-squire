import { IconX } from "@tabler/icons-react";
import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import NotFound from "./NotFound";
import OpeningNotice from "./OpeningNotice";
import PaidStamp from "./PaidStamp";
import PaymentPanel from "./PaymentPanel";
import TeamsTab from "./TeamsTab";
import { type HomeTab } from "./FencerShell";
import { home } from "./routes";
import { amendmentOpen, registrationStatus } from "./openingMoment";
import { useOpeningMoment } from "./useOpeningMoment";
import { useTabBand } from "./useTabBand";
import { type Availability, type RegistrationDetail, type TournamentDetail as TournamentDetailData, api } from "./api";
import { formatMoneyWithEur } from "./money";
import {
  DiscountList,
  DisciplinesInfo,
  InfoHeader,
  OtherActionsInfo,
  RegistrationForm,
} from "./TournamentFace";

function RegistrationStateTag({
  registration,
  detail,
}: {
  registration: RegistrationDetail;
  detail: TournamentDetailData;
}) {
  const { t } = useTranslation();
  // A reservation on a payments-off tournament is not awaiting anything: no
  // money was asked for and no window is running, so it reads as confirmed
  // rather than as reserved (spec: fencer-home).
  const state =
    registration.state === "reserved" && !detail.feature_payments ? "paid" : registration.state;
  const label = t(`registration.state.${state}`);
  if (state === "paid") return <PaidStamp id={registration.vs} label={label} />;
  if (state === "reserved") return <span className="tag tag-form-yellow">{label}</span>;
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
      {/* A queued placement carries no amount: the queue holds no money, and a
          fee beside it would not be in the total below — on a registration that
          holds a seat as well as a queue place, the lines would not sum. */}
      {substitutes.map((e) => (
        <AmountLine
          key={e.slug}
          className="muted"
          label={`${discipline.get(e.slug)?.name ?? e.slug} — ${t("registration.queuePosition", {
            position: e.queue_position,
          })}`}
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
          amount={
            team.waitlisted ? undefined : formatMoneyWithEur(team.fee, team.fee_eur, detail)
          }
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
      {/* what the discounts took off, between the priced lines and the total
          they explain: every line above is a list price, so an applied
          discount is the only thing that makes the two agree. A configured
          discount the selection did not activate is not a line — it deducted
          nothing and belongs to the tournament's information screen, not to
          this statement of what was charged. */}
      {registration.discounts
        .filter((d) => d.applied)
        .map((d, index) => (
          <AmountLine
            key={`discount-${index}`}
            label={d.name}
            amount={
              d.deducted === null
                ? undefined
                : t("discounts.amountValue", {
                    amount: formatMoneyWithEur(
                      d.deducted,
                      d.deducted_eur === null ? null : d.deducted_eur,
                      detail,
                    ),
                  })
            }
          />
        ))}
      <AmountLine
        className="amount-total"
        label={t("form.totalLabel")}
        amount={formatMoneyWithEur(registration.total_amount, registration.total_eur, detail)}
      />
      {/* what the tournament costs is information the fencer needs; what is
          outstanding is a demand, and a payments-off tournament makes none
          (spec: fencer-home) */}
      {detail.feature_payments &&
        (Number(registration.outstanding_amount) !== 0 ||
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
      <div className="rail-card-heading">
        <h2>{t("registration.title")}</h2>
        <RegistrationStateTag registration={registration} detail={detail} />
      </div>
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
}: {
  slug: string;
  detail: TournamentDetailData;
  registration: RegistrationDetail;
  canAmend: boolean;
  onAmend: () => void;
  onCancelled: () => void;
}) {
  const { t } = useTranslation();
  // which destructive action is awaiting its confirmation, if any — the two
  // share one slot, so neither can be confirmed behind the other
  const [confirming, setConfirming] = useState<"amend" | "cancel" | null>(null);
  const [busy, setBusy] = useState(false);

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

  return (
    <section className="rail-card">
      <div className="rail-card-heading">
        <h2>{t("registration.title")}</h2>
        <RegistrationStateTag registration={registration} detail={detail} />
      </div>

      <RegistrationLines registration={registration} detail={detail} />

      {/* nothing is being asked for while payments are off: no account to
          quote, no variable symbol in use and no expiry to state, and a
          partial set would tell the fencer to do something the tournament is
          not asking of them (spec: fencer-home) */}
      {registration.state === "reserved" && detail.feature_payments && (
        <PaymentPanel slug={slug} />
      )}

      {/* amend and cancel both rewrite something the fencer already holds, so
          both are destructive controls behind a confirmation, standing as one
          centered pair (spec design-system: "Destructive actions") */}
      {confirming !== null ? (
        <div className="rail-card dashed">
          <p>
            {/* a paid cancellation says neither that the fee is refundable nor
                that it is not: refunds are settled with the organizer outside
                the system, and `refundable_until` is no longer settable, so
                asserting either way would be a promise (design Risks) */}
            {confirming === "amend"
              ? t("registration.amendConfirm")
              : registration.state === "paid"
                ? t("cancel.paidConfirm")
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
  // held registration, with an amendment opening in place of the latter; the
  // third tab, offered only alongside a held team, carries every roster
  // editor (design team-disciplines D1)
  const [tab, setTab] = useState<"tournament" | "registration" | "teams">("tournament");
  // keeps the selected tab visible when the three tabs scroll below 768px
  const band = useTabBand(tab);
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

  // the wait for registration to open: no polling, one scheduled unlock, and
  // a refresh at the moment so the seat counts the form opens on are current
  // (design add-registration-open-time D8)
  const opening = useOpeningMoment(detail, refresh);

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
    registrationStatus(detail, opening.now) === "open" &&
    hasOpenSlot;
  const canAmend =
    !readOnly &&
    detail !== null &&
    registration !== null &&
    (registration.state === "reserved" || registration.state === "paid") &&
    amendmentOpen(detail, opening.now);
  const secondTabOffered = hasActive || canRegister;
  // offered only alongside a held team, on a registration that is still
  // active and a tournament not yet held (design team-disciplines D5)
  const teamsTabOffered = !readOnly && hasActive && (registration?.teams.length ?? 0) > 0;

  // a cancellation on a closed tournament can drop both `hasActive` and
  // `canRegister` at once — fall back before a selected-but-absent tab (or a
  // stale in-progress amendment) can be reached (design D3, task 4.4)
  useEffect(() => {
    if (!secondTabOffered) {
      setTab("tournament");
      setAmending(false);
    } else if (tab === "teams" && !teamsTabOffered) {
      // an amendment removing the last team, or a cancellation, can withdraw
      // the teams tab out from under the fencer standing on it (design
      // team-disciplines D5)
      setTab("tournament");
    }
  }, [secondTabOffered, teamsTabOffered, tab]);

  /** Leaving the registration tab abandons any amendment in progress — the
   *  page introduces no separate cancel control for it (design D3); this
   *  covers the teams tab for free since the guard is `next !== "registration"`. */
  function selectTab(next: "tournament" | "registration" | "teams") {
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
        <nav className="stage-control detail-tabs stage-control-band" ref={band}>
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
          {teamsTabOffered && (
            <button
              className={tab === "teams" ? "active" : ""}
              onClick={() => selectTab("teams")}
            >
              {t("detail.tabs.teams")}
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
              {!readOnly &&
                !secondTabOffered &&
                (registrationStatus(detail, opening.now) === "opens_on" ? (
                  <OpeningNotice
                    detail={detail}
                    remainingMs={opening.remainingMs}
                    counting={opening.counting}
                  />
                ) : (
                  <section className="rail-card dashed">
                    <p className="rail-hint">{t("detail.closedNotice")}</p>
                  </section>
                ))}
            </>
          ) : tab === "teams" && registration ? (
            <TeamsTab
              slug={slug}
              teams={registration.teams}
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
                // back to the information screen, which re-derives the wait
                // from a fresh payload — the countdown included
                onNotYetOpen: () => {
                  setTab("tournament");
                  refresh();
                },
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
