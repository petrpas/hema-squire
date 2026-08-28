import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { Organizer } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import SuggestionAnchor from "../SuggestionAnchor";
import SuggestionList from "../SuggestionList";
import { organizerEntries, type SuggestionEntry } from "../suggestions";
import { useSuggestions } from "../useSuggestions";
import type { FieldError as FieldErrorValue } from "../validation";

/** One titular organizer: a name, its link, and the control that removes the
 *  pair. A row of its own because each name field carries its own suggestion
 *  list, and a hook cannot be called from inside the section's map. */
export default function OrganizerRow({
  organizer,
  index,
  candidates,
  errors,
  registerRef,
  onPatch,
  onRemove,
  onTouch,
  onClearIfValid,
  nameCheck,
  linkCheck,
}: {
  organizer: Organizer;
  index: number;
  candidates: Organizer[];
  errors: Record<string, FieldErrorValue | undefined>;
  registerRef: (key: string, el: HTMLInputElement | null) => void;
  onPatch: (index: number, fields: Partial<Organizer>) => void;
  onRemove: (index: number) => void;
  onTouch: (key: string, check: () => FieldErrorValue | null) => void;
  onClearIfValid: (key: string, check: () => FieldErrorValue | null) => void;
  nameCheck: (index: number, value: string) => FieldErrorValue | null;
  linkCheck: (index: number, value: string) => FieldErrorValue | null;
}) {
  const { t } = useTranslation();

  // The name and the link travel together: choosing a remembered club fills
  // both in one patch, so the save bar counts one change rather than two, and a
  // club remembered without a link leaves the link empty rather than stale.
  const suggestions = useSuggestions(
    organizerEntries(candidates),
    organizer.name,
    (entry: SuggestionEntry) => {
      onPatch(index, { name: entry.value, link: entry.secondary ?? null });
      onClearIfValid(`name-${index}`, () => nameCheck(index, entry.value));
      onClearIfValid(`link-${index}`, () => linkCheck(index, entry.secondary ?? ""));
    },
  );

  return (
    <tr>
      <td>
        <SuggestionAnchor active>
          <input
            ref={(el) => registerRef(`name-${index}`, el)}
            className="cell-input"
            value={organizer.name}
            placeholder={t("setup.organizers.placeholder")}
            onChange={(event) => {
              onPatch(index, { name: event.target.value });
              onClearIfValid(`name-${index}`, () => nameCheck(index, event.target.value));
            }}
            onBlur={(event) => {
              suggestions.close();
              onTouch(`name-${index}`, () => nameCheck(index, event.target.value));
            }}
            {...suggestions.inputProps}
            {...invalidProps(`name-${index}`, errors[`name-${index}`])}
          />
          <SuggestionList suggestions={suggestions} label={t("setup.suggestions.organizers")} />
        </SuggestionAnchor>
        <FieldError field={`name-${index}`} error={errors[`name-${index}`]} />
      </td>
      <td>
        <input
          ref={(el) => registerRef(`link-${index}`, el)}
          className="cell-input"
          value={organizer.link ?? ""}
          placeholder={t("setup.organizers.linkPlaceholder")}
          onChange={(event) => {
            onPatch(index, { link: event.target.value });
            onClearIfValid(`link-${index}`, () => linkCheck(index, event.target.value));
          }}
          onBlur={(event) => onTouch(`link-${index}`, () => linkCheck(index, event.target.value))}
          {...invalidProps(`link-${index}`, errors[`link-${index}`])}
        />
        <FieldError field={`link-${index}`} error={errors[`link-${index}`]} />
      </td>
      <td className="col-actions">
        <button className="row-action" title={t("actions.delete")} onClick={() => onRemove(index)}>
          <IconX size={16} stroke={1.5} />
        </button>
      </td>
    </tr>
  );
}
