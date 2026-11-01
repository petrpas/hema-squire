import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { FencerTournament } from "./api";
import InlineProse from "./InlineProse";
import { zoneAbbreviation } from "./openingMoment";

/** One labelled fact. A fact with nothing to state is not rendered at all, so
 *  the grid closes up rather than showing a label over an empty cell. */
function Fact({
  label,
  wide = false,
  children,
}: {
  label: string;
  /** Takes the whole row: a list of names has no second column to share. */
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="detail-fact" data-wide={wide || undefined}>
      <dt>{label}</dt>
      {children}
    </div>
  );
}

/** The tournament's facts under its title: when, where, who may enter, when
 *  registration runs, and who organizes it (spec fencer-home). */
export default function DetailFacts({ detail }: { detail: FencerTournament }) {
  const { t } = useTranslation();
  const city = detail.city?.trim() ? detail.city : null;
  const address = detail.address?.trim() ? detail.address : null;
  const opens = detail.registration_opens;
  const closes = detail.registration_closes;
  const hasPlace = city !== null || address !== null;

  return (
    <dl className="detail-facts">
      <Fact label={t("detail.factDate")}>
        <dd>{new Date(detail.date).toLocaleDateString("cs")}</dd>
      </Fact>
      {hasPlace && (
        <Fact label={t("detail.factPlace")}>
          {city !== null && <dd>{city}</dd>}
          {address !== null && (
            <dd className="detail-address">
              <InlineProse source={address} />
            </dd>
          )}
        </Fact>
      )}
      <Fact label={t("detail.factEntry")}>
        <dd>
          {detail.qualification_open
            ? t("detail.qualificationOpen")
            : t("detail.qualificationRequired", { criteria: detail.qualification_criteria })}
        </dd>
      </Fact>
      {(opens || closes) && (
        <Fact label={t("detail.factRegistration")}>
          {opens && (
            <dd>
              {detail.registration_opens_time
                ? // the hour the organizer named, with the zone it is named in:
                  // without the zone the hour is only true where the tournament
                  // is (spec: fencer-home)
                  t("detail.opensAt", {
                    date: new Date(opens).toLocaleDateString("cs"),
                    time: detail.registration_opens_time.slice(0, 5),
                    zone: zoneAbbreviation(detail),
                  })
                : t("detail.opensOn", { date: new Date(opens).toLocaleDateString("cs") })}
            </dd>
          )}
          {closes && (
            <dd>{t("detail.closesOn", { date: new Date(closes).toLocaleDateString("cs") })}</dd>
          )}
        </Fact>
      )}
      {detail.organizers.length > 0 && (
        <Fact label={t("detail.factOrganizers")} wide>
          <dd>
            {detail.organizers.map((organizer, index) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: a read-only list rebuilt from props; position is the only identity these rows have
              <span key={index}>
                {index > 0 && ", "}
                {organizer.link ? (
                  <a
                    className="detail-inline-link"
                    href={organizer.link}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {organizer.name}
                  </a>
                ) : (
                  organizer.name
                )}
              </span>
            ))}
          </dd>
        </Fact>
      )}
    </dl>
  );
}
