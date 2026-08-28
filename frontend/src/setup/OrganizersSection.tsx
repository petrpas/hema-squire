import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type Organizer, type SetupSuggestions, type TournamentDetail, api } from "../api";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString, checkUrl, type FieldError as FieldErrorValue } from "../validation";
import OrganizerRow from "./OrganizerRow";
import { type SaverRegistry, useSectionSaver } from "./shared";

export function OrganizersSection({
  detail,
  slug,
  registry,
  suggestions,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
  suggestions: SetupSuggestions;
}) {
  const { t } = useTranslation();
  const [organizers, setOrganizers] = useState<Organizer[]>(detail.organizers);
  const [dirty, setDirty] = useState(false);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    setOrganizers(detail.organizers);
    validation.clearAll();
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  function patch(index: number, fields: Partial<Organizer>) {
    const next = [...organizers];
    next[index] = { ...next[index], ...fields };
    setOrganizers(next);
    setDirty(true);
  }

  function nameCheck(index: number, value: string): FieldErrorValue | null {
    const error = checkString(`name-${index}`, "OrganizerIn.name", value, { required: true });
    return error;
  }

  function linkCheck(index: number, value: string): FieldErrorValue | null {
    return checkUrl(`link-${index}`, "OrganizerIn.link", value);
  }

  function everyCheck(): Array<() => FieldErrorValue | null> {
    return organizers.flatMap((organizer, index) => [
      () => nameCheck(index, organizer.name),
      () => linkCheck(index, organizer.link ?? ""),
    ]);
  }

  useSectionSaver(registry, "tournament", "organizers", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () => validation.validateAll(everyCheck()),
    focusFirstInvalid: () => {
      for (let index = 0; index < organizers.length; index++) {
        if (nameCheck(index, organizers[index].name)) {
          fieldRefs.current[`name-${index}`]?.focus();
          return;
        }
        if (linkCheck(index, organizers[index].link ?? "")) {
          fieldRefs.current[`link-${index}`]?.focus();
          return;
        }
      }
    },
    flush: async () => {
      try {
        await api.updateTournament(slug, {
          organizers: organizers
            .map((o) => ({ name: o.name.trim(), link: o.link?.trim() || null }))
            .filter((o) => o.name.length > 0),
        });
        setDirty(false);
        return [{ change: "organizers", section: "organizers", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        return [{ change: "organizers", section: "organizers", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.organizers.title")}</h2>
      <table className="sheet-table">
        <tbody>
          {organizers.map((organizer, index) => (
            <OrganizerRow
              key={index}
              organizer={organizer}
              index={index}
              candidates={suggestions.organizers}
              errors={validation.errors}
              registerRef={(key, el) => {
                fieldRefs.current[key] = el;
              }}
              onPatch={patch}
              onRemove={(at) => {
                setOrganizers(organizers.filter((_, i) => i !== at));
                setDirty(true);
              }}
              onTouch={validation.touch}
              onClearIfValid={validation.clearIfValid}
              nameCheck={nameCheck}
              linkCheck={linkCheck}
            />
          ))}
        </tbody>
      </table>
      <button
        className="link-button"
        onClick={() => {
          setOrganizers([...organizers, { name: "", link: null }]);
          setDirty(true);
        }}
      >
        + {t("setup.organizers.add")}
      </button>
    </section>
  );
}
