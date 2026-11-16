import { useTranslation } from "react-i18next";

import type { FloorDiscipline, FloorOfficial, FloorOfficialOut, Role } from "../floorApi";
import {
  DayTicks,
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
} from "./shared";

const ROLES: Role[] = ["referee", "judge", "table"];

/** The tournament's officials: name, an optional link to the person they are
 *  on the roster, roles, disciplines and days (spec floor-setup, Officials
 *  and their availability). A link whose person left is stated, not dropped. */
export function OfficialsSection({
  slug,
  onSaved,
  onDirty,
  officials,
  disciplines,
  persons,
  days,
}: SectionProps & {
  officials: FloorOfficialOut[];
  disciplines: FloorDiscipline[];
  persons: { key: string; name: string }[];
  days: string[];
}) {
  const { t } = useTranslation();
  const stored = officials.map(({ link_lost: _lost, ...official }) => official);
  const lost = new Set(officials.filter((o) => o.link_lost).map((o) => o.id));
  const [draft, setDraft, dirty] = useDraft<FloorOfficial[]>(stored, "officials", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "officials", onSaved);
  const errorAt = useErrorText(errors);

  function patch(index: number, fields: Partial<FloorOfficial>) {
    setDraft(draft.map((official, i) => (i === index ? { ...official, ...fields } : official)));
  }

  function toggle<T>(list: T[], value: T, on: boolean): T[] {
    return on ? [...list, value] : list.filter((other) => other !== value);
  }

  return (
    <SectionCard
      title={t("floor.setup.officials.title")}
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      {draft.length === 0 && <p className="muted">{t("floor.setup.officials.none")}</p>}
      {draft.map((official, index) => (
        <div key={official.id ?? `new-${index}`} className="floor-row">
          <label>
            {t("floor.setup.officials.name")}
            <input
              value={official.name}
              maxLength={200}
              onChange={(event) => patch(index, { name: event.target.value })}
            />
            <FieldNote text={errorAt(`${index}.name`)} />
          </label>
          <label>
            {t("floor.setup.officials.person")}
            <select
              value={official.person_key ?? ""}
              onChange={(event) => patch(index, { person_key: event.target.value || null })}
            >
              <option value="">{t("floor.setup.officials.noPerson")}</option>
              {official.person_key !== null &&
                !persons.some((p) => p.key === official.person_key) && (
                  <option value={official.person_key}>
                    {t("floor.setup.officials.lostOption")}
                  </option>
                )}
              {persons.map((person) => (
                <option key={person.key} value={person.key}>
                  {person.name}
                </option>
              ))}
            </select>
            {official.id !== null && lost.has(official.id) && (
              <span className="floor-missing">{t("floor.setup.officials.linkLost")}</span>
            )}
            <FieldNote text={errorAt(`${index}.person_key`)} />
          </label>
          <fieldset className="floor-ticks">
            <legend>{t("floor.setup.officials.roles")}</legend>
            {ROLES.map((role) => (
              <label key={role}>
                <input
                  type="checkbox"
                  checked={official.roles.includes(role)}
                  onChange={(event) =>
                    patch(index, { roles: toggle(official.roles, role, event.target.checked) })
                  }
                />
                {t(`floor.roles.${role}`)}
              </label>
            ))}
            <FieldNote text={errorAt(`${index}.roles`)} />
          </fieldset>
          <fieldset className="floor-ticks">
            <legend>{t("floor.setup.officials.disciplines")}</legend>
            {disciplines.map((discipline) => (
              <label key={discipline.id}>
                <input
                  type="checkbox"
                  checked={official.discipline_ids.includes(discipline.id)}
                  onChange={(event) =>
                    patch(index, {
                      discipline_ids: toggle(
                        official.discipline_ids,
                        discipline.id,
                        event.target.checked,
                      ),
                    })
                  }
                />
                {discipline.name}
              </label>
            ))}
          </fieldset>
          {days.length > 1 && (
            <DayTicks
              days={days}
              chosen={official.days}
              label={t("floor.setup.officials.days")}
              onChange={(chosen) => patch(index, { days: chosen })}
            />
          )}
          <button
            type="button"
            className="secondary"
            onClick={() => setDraft(draft.filter((_, i) => i !== index))}
          >
            {t("floor.setup.remove")}
          </button>
        </div>
      ))}
      <button
        type="button"
        className="secondary"
        onClick={() =>
          setDraft([
            ...draft,
            {
              id: null,
              name: "",
              person_key: null,
              roles: ["referee"],
              discipline_ids: disciplines.map((d) => d.id),
              days,
            },
          ])
        }
      >
        {t("floor.setup.officials.add")}
      </button>
    </SectionCard>
  );
}
