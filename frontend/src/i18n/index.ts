import i18n from "i18next";
import { initReactI18next } from "react-i18next";

// Any ./<code>.json becomes a language — adding a locale needs no code change.
const modules = import.meta.glob<{ default: Record<string, unknown> }>("./*.json", {
  eager: true,
});

const resources = Object.fromEntries(
  Object.entries(modules).map(([path, mod]) => [
    path.replace(/^\.\/(.+)\.json$/, "$1"),
    { translation: mod.default },
  ]),
);

/** The locale a visitor reads before any account has said otherwise: English,
 *  this application's default and its fallback. A public screen therefore
 *  renders in it from the first paint rather than being swapped after one,
 *  and it is what the sign-in screen is pinned to anyway.
 *
 *  Czech is complete too, but it is a choice an account makes, not the
 *  language an anonymous page is written in (spec `localization`). */
i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
