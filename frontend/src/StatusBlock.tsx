import { useTranslation } from "react-i18next";
import type { OpenTournament } from "./api";
import { openingHourIn } from "./openingMoment";

/** A day as the card states it: day and month, the year being the card's own
 *  date line's business. */
function shortDay(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("cs", { day: "numeric", month: "numeric" });
}

type Tone = "open" | "pending" | "elsewhere" | "closed";

function Block({ tone, lines }: { tone: Tone; lines: (string | null)[] }) {
  const [first, ...rest] = lines.filter((line): line is string => line !== null);
  return (
    <p className="status-block" data-tone={tone}>
      <span className="status-block-head">{first}</span>
      {rest.map((line, index) => (
        // the last line of three is a date or an hour, set as data
        <span key={line} className={index === 1 ? "status-block-data" : undefined}>
          {line}
        </span>
      ))}
    </p>
  );
}

/** Registration's state, as the card's cover states it (spec `fencer-home`):
 *  three short lines, the last a date or an hour where there is one. Absent
 *  lines are omitted, never rendered empty. The status itself is the server's,
 *  computed against the same resolved moment the detail page reads, so the
 *  card, the tabs and the page cannot disagree at the boundary. */
export function StatusBlock({ tournament }: { tournament: OpenTournament }) {
  const { t } = useTranslation();
  const head = t("home.block.registration");
  switch (tournament.registration_status) {
    case "open":
      return (
        <Block
          tone="open"
          lines={[
            head,
            t("home.block.open"),
            tournament.registration_closes_on
              ? t("home.block.until", { date: shortDay(tournament.registration_closes_on) })
              : null,
          ]}
        />
      );
    case "opens_on": {
      // the hour is stated only where the organizer set one (change
      // add-registration-open-time)
      const hour = openingHourIn(tournament.registration_opens_at, tournament.timezone);
      return (
        <Block
          tone="pending"
          lines={[
            head,
            tournament.registration_opens_on
              ? t("home.block.from", { date: shortDay(tournament.registration_opens_on) })
              : null,
            hour ? t("home.block.at", { time: hour }) : null,
          ]}
        />
      );
    }
    case "elsewhere":
      // where registration is, never that it is closed: this tournament never
      // had a window here (design add-registrations-kept-by D4)
      return <Block tone="elsewhere" lines={[head, t("home.block.elsewhere")]} />;
    default:
      return <Block tone="closed" lines={[head, t("home.block.closed")]} />;
  }
}

/** The account's own bond to a listed tournament, on the Mine and Past tabs:
 *  its registration state where it holds or held one, an organizer mark where
 *  that is the only bond, and the registration status otherwise. */
export function BondBlock({ tournament }: { tournament: OpenTournament }) {
  const { t } = useTranslation();
  const state = tournament.my_registration_state;
  // Absent, not "none", when there is no account behind the page — a visitor
  // without one has no standing to state (spec `public-browsing`).
  if (state !== undefined && state !== "none") {
    return (
      <Block
        tone={state === "cancelled" ? "closed" : "pending"}
        lines={[t("home.block.registration"), t(`registration.state.${state}`)]}
      />
    );
  }
  if (tournament.organized === true) {
    return <Block tone="pending" lines={[t("home.organized")]} />;
  }
  return <StatusBlock tournament={tournament} />;
}
