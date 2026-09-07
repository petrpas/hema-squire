import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>{t("notFound.title")}</h1>
        <p>{t("notFound.body")}</p>
        <Link to="/">{t("notFound.home")}</Link>
      </div>
    </div>
  );
}
