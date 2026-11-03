import { useTranslation } from "react-i18next";

/** One section of the notice as the locale files hold it. */
interface Section {
  title: string;
  paragraphs: string[];
}

/** The public privacy notice (spec `privacy`, A public privacy page states
 *  how personal data is handled). Its text lives in the locale files, so it is
 *  versioned with the code and read in a diff (design privacy-baseline D3);
 *  this component only lays it out. */
export default function PrivacyPage() {
  const { t } = useTranslation();
  const sections = t("privacy.page.sections", { returnObjects: true }) as Section[];
  return (
    <div className="workspace privacy-page">
      <article className="rail-card">
        <h1>{t("privacy.page.title")}</h1>
        {sections.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </section>
        ))}
        <p className="rail-hint">{t("privacy.page.effective")}</p>
      </article>
    </div>
  );
}
