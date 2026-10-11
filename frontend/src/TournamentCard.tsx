import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { OpenTournament } from "./api";
import CapacityMeter from "./CapacityMeter";
import DotJoined from "./DotJoined";
import FamiliarFaces from "./FamiliarFaces";
import type { HomeTab } from "./FencerShell";
import PaidStamp from "./PaidStamp";
import { consolePath, detail } from "./routes";
import { BondBlock, StatusBlock } from "./StatusBlock";
import { CoverPlate, coverTint } from "./TournamentCover";

/** The card's place in the list as shown, in the ledger's zero-padded form. */
function ordinal(position: number): string {
  return String(position).padStart(3, "0");
}

/** One entry of the list (spec `fencer-home`, Fencer Home landing).
 *
 *  The card is a container rather than one big link, because an organizer's
 *  Manage control is a link of its own and a nested interactive element inside
 *  an anchor is invalid and behaves unpredictably (design Decision 6). The
 *  card's whole body remains the link to the tournament, so nothing inside it
 *  is a link: the organizer names are text. */
export default function TournamentCard({
  tournament,
  tab,
  position,
}: {
  tournament: OpenTournament;
  tab: HomeTab;
  /** 1-based, in the list as rendered. */
  position: number;
}) {
  const { t } = useTranslation();
  const bond = tab === "past" || tab === "mine";
  return (
    <li className="home-card">
      <Link className="home-card-body" to={detail(tournament.slug)} state={{ tab }}>
        {/* which color each tint means is the stylesheet's business, not
            this file's */}
        <div className="home-card-cover" data-tint={coverTint(tournament)}>
          {bond ? <BondBlock tournament={tournament} /> : <StatusBlock tournament={tournament} />}
          <span className="home-card-ordinal">{ordinal(position)}</span>
          <CoverPlate
            subject={tournament}
            className="home-card-plate"
            ring={tournament.registration_status === "open" ? "open" : "rest"}
          />
          {bond && tournament.my_registration_state === "paid" && (
            <span className="home-card-stamp">
              <PaidStamp id={tournament.slug} label={t("registration.state.paid")} />
            </span>
          )}
        </div>
        <div className="home-card-main">
          <h2>{tournament.display_name}</h2>
          {tournament.subtitle && <p className="home-card-subtitle">{tournament.subtitle}</p>}
          {/* the town alone, as plain text: everyone knows where Brno is, and
              where in town is read on the tournament's own page */}
          <DotJoined
            className="home-card-when"
            parts={[
              new Date(tournament.date).toLocaleDateString("cs"),
              tournament.city?.trim() ? tournament.city : null,
            ]}
          />
          {tournament.organizers.length > 0 && (
            <p className="home-card-organizers">
              {tournament.organizers.map((organizer) => organizer.name).join(", ")}
            </p>
          )}
        </div>
        {tournament.disciplines.length > 0 && (
          <ul className="meters">
            {tournament.disciplines.map((d) => (
              <CapacityMeter key={d.slug} discipline={d} />
            ))}
          </ul>
        )}
        <div className="home-card-foot">
          {tournament.familiar !== undefined && <FamiliarFaces familiar={tournament.familiar} />}
          {tournament.entrant_count > 0 && (
            <span className="home-card-counts">
              {t("home.counts.fencers", { count: tournament.entrant_count })}
              {" · "}
              {t("home.counts.clubs", { count: tournament.club_count })}
            </span>
          )}
        </div>
      </Link>
      {/* Present only for an account that may manage this tournament, and the
          only thing that makes an organizer's list differ from anyone else's
          (spec `fencer-home`, Managing a tournament from its card). A link,
          so middle-click opens the console in a new tab. */}
      {tournament.organized === true && (
        <Link className="button-quiet home-card-manage" to={consolePath(tournament.slug)}>
          {t("home.manage")}
        </Link>
      )}
    </li>
  );
}
