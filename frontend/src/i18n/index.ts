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

i18n.use(initReactI18next).init({
  resources,
  lng: "cs",
  fallbackLng: "cs",
  interpolation: { escapeValue: false },
});

export default i18n;
