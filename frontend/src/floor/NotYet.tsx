import { useTranslation } from "react-i18next";

/** A tab whose change has not landed: stated in one line, never hidden, so a
 *  later change fills it without moving the band (spec floor-console). */
export default function NotYet() {
  const { t } = useTranslation();
  return <p className="floor-not-yet muted">{t("floor.notYet")}</p>;
}
