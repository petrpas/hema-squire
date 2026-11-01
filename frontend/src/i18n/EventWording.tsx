import type { ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import i18n from "./index";

/** The same catalogue, reading each key's `_event` variant where it has one and
 *  its plain form where it has not (spec `discipline-less-events`, The word
 *  follows the kind). Only a string that can appear on an event needs a variant,
 *  so one that exists beside disciplines stays as it is. */
const eventI18n = i18n.cloneInstance();
const fixedT = eventI18n.getFixedT.bind(eventI18n);
eventI18n.getFixedT = ((...args: Parameters<typeof fixedT>) => {
  const translate = fixedT(...args);
  return (key: string, options?: object) => translate(key, { context: "event", ...options });
}) as typeof fixedT;
i18n.on("languageChanged", (language) => {
  void eventI18n.changeLanguage(language);
});

/** What a component owning the record reads with, since it sits above
 *  `EventWording` and cannot be under it. */
export function wordingI18n(isEvent: boolean) {
  return isEvent ? eventI18n : i18n;
}

/** Everything under it names one record, and calls it by what it is. */
export default function EventWording({
  isEvent,
  children,
}: {
  isEvent: boolean;
  children: ReactNode;
}) {
  return isEvent ? <I18nextProvider i18n={eventI18n}>{children}</I18nextProvider> : children;
}
