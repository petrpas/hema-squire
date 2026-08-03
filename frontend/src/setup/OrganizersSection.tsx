import { IconX } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type Organizer, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString, checkUrl, type FieldError as FieldErrorValue } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

export function OrganizersSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
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
            <tr key={index}>
              <td>
                <input
                  ref={(el) => {
                    fieldRefs.current[`name-${index}`] = el;
                  }}
                  className="cell-input"
                  value={organizer.name}
                  placeholder={t("setup.organizers.placeholder")}
                  onChange={(event) => {
                    patch(index, { name: event.target.value });
                    validation.clearIfValid(`name-${index}`, () => nameCheck(index, event.target.value));
                  }}
                  onBlur={(event) => validation.touch(`name-${index}`, () => nameCheck(index, event.target.value))}
                  {...invalidProps(`name-${index}`, validation.errors[`name-${index}`])}
                />
                <FieldError field={`name-${index}`} error={validation.errors[`name-${index}`]} />
              </td>
              <td>
                <input
                  ref={(el) => {
                    fieldRefs.current[`link-${index}`] = el;
                  }}
                  className="cell-input"
                  value={organizer.link ?? ""}
                  placeholder={t("setup.organizers.linkPlaceholder")}
                  onChange={(event) => {
                    patch(index, { link: event.target.value });
                    validation.clearIfValid(`link-${index}`, () => linkCheck(index, event.target.value));
                  }}
                  onBlur={(event) => validation.touch(`link-${index}`, () => linkCheck(index, event.target.value))}
                  {...invalidProps(`link-${index}`, validation.errors[`link-${index}`])}
                />
                <FieldError field={`link-${index}`} error={validation.errors[`link-${index}`]} />
              </td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  onClick={() => {
                    setOrganizers(organizers.filter((_, i) => i !== index));
                    setDirty(true);
                  }}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
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
