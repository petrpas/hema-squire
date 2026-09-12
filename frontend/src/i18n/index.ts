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

/** The locale a visitor reads before any account has said otherwise: Czech,
 *  this application's default and its fallback — the one locale guaranteed
 *  complete (spec `localization`). A public screen therefore renders in it
 *  from the first paint rather than being swapped after one.
 *
 *  Not the English the sign-in screen uses: that screen is pinned to English
 *  by its own requirement, and an account's *stored* default being English is
 *  a fact about accounts, not about what an anonymous page is written in. */
i18n.use(initReactI18next).init({
  resources,
  lng: "cs",
  fallbackLng: "cs",
  interpolation: { escapeValue: false },
});

export default i18n;
