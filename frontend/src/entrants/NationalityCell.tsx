import { useTranslation } from "react-i18next";

import { flagUrl, GREYSCALE_FLAGS } from "./flags";

/** The country's name in the page's language, or its code where the
 *  runtime knows no name for it. */
function countryName(country: string, language: string): string {
  try {
    return new Intl.DisplayNames([language], { type: "region" }).of(country) ?? country;
  } catch {
    return country;
  }
}

/** A roster's Nat. cell: a country the server could read is drawn as its
 *  flag, named in the page's language for hover and screen readers; a
 *  nationality no country is read from is stated as written (spec
 *  public-entrants, Nationality is stated as a flag). */
export default function NationalityCell({
  nationality,
  country,
}: {
  nationality: string | null;
  country: string | null;
}) {
  const { i18n } = useTranslation();
  const url = country ? flagUrl(country) : undefined;
  if (!country || !url) return <td className="col-nat">{nationality}</td>;
  const name = countryName(country, i18n.language);
  const className = GREYSCALE_FLAGS.has(country)
    ? "entrant-flag entrant-flag-mono"
    : "entrant-flag";
  return (
    <td className="col-nat">
      <img className={className} src={url} alt={name} title={name} />
    </td>
  );
}
