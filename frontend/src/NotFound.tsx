import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export default function NotFound() {
  const { t } = useTranslation();

  // Night wherever it is reached from, so its appearance says nothing about
  // which kind of address led here (spec routing).
  return (
    <div className="login-page" data-skin="night">
      <div className="login-card">
        <h1>{t("notFound.title")}</h1>
        <p>{t("notFound.body")}</p>
        <Link to="/">{t("notFound.home")}</Link>
      </div>
    </div>
  );
}
