import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { FloorDiscipline, FloorOfficial, FloorOfficialOut } from "../floorApi";
import { ServesDialog, servesText } from "./ServesDialog";
import {
  DayTicks,
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
} from "./shared";

/** The tournament's referees (spec floor-setup, Officials and their
 *  availability). "Šermuje jako" comes first: a referee who fences is named by
 *  their roster person, and the name field greys out. Each discipline is
 *  served as regular or as reserve; days are asked only on a tournament of
 *  several days. A link whose person left is stated, not dropped. */
export function OfficialsTab({
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
  /** Empty on a one-day tournament: every referee is there on the day. */
  days: string[];
}) {
  const { t } = useTranslation();
  const stored = officials.map(({ link_lost: _lost, ...official }) => official);
  const lost = new Set(officials.filter((o) => o.link_lost).map((o) => o.id));
  const [draft, setDraft, dirty] = useDraft<FloorOfficial[]>(stored, "officials", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "officials", onSaved);
  const errorAt = useErrorText(errors);
  const [editing, setEditing] = useState<number | null>(null);
  const open = editing === null ? undefined : draft[editing];
  const nameOf = new Map(persons.map((p) => [p.key, p.name]));

  function patch(index: number, fields: Partial<FloorOfficial>) {
    setDraft(draft.map((official, i) => (i === index ? { ...official, ...fields } : official)));
  }

  function link(index: number, key: string | null) {
    const official = draft[index];
    if (official === undefined) return;
    // the fencer's name is the referee's; unlinking keeps it to edit
    const name = key !== null ? (nameOf.get(key) ?? official.name) : official.name;
    patch(index, { person_key: key, name });
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
            {t("floor.setup.officials.person")}
            <select
              value={official.person_key ?? ""}
              onChange={(event) => link(index, event.target.value || null)}
            >
              <option value="">{t("floor.setup.officials.noPerson")}</option>
              {official.person_key !== null && !nameOf.has(official.person_key) && (
                <option value={official.person_key}>{t("floor.setup.officials.lostOption")}</option>
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
          <label>
            {t("floor.setup.officials.name")}
            <input
              value={official.name}
              maxLength={200}
              disabled={official.person_key !== null}
              onChange={(event) => patch(index, { name: event.target.value })}
            />
            <FieldNote text={errorAt(`${index}.name`)} />
          </label>
          <label className="floor-check">
            <input
              type="checkbox"
              checked={official.main}
              onChange={(event) => patch(index, { main: event.target.checked })}
            />
            {t("floor.setup.officials.main")}
          </label>
          <div className="floor-serves">
            <span className="floor-serves-label">{t("floor.setup.officials.disciplines")}</span>
            <span>
              {servesText(
                official.serves,
                disciplines,
                t("floor.setup.serves.reserve"),
                t("floor.setup.officials.noDiscipline"),
              )}
            </span>
            <button type="button" className="secondary" onClick={() => setEditing(index)}>
              {t("floor.setup.edit")}
            </button>
            <FieldNote text={errorAt(`${index}.serves.0`)} />
          </div>
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
              main: true,
              serves: disciplines.map((d) => ({ discipline_id: d.id, reserve: false })),
              days,
            },
          ])
        }
      >
        {t("floor.setup.officials.add")}
      </button>
      {open !== undefined && editing !== null && (
        <ServesDialog
          title={t("floor.setup.officials.servesTitle", {
            name: open.name || t("floor.setup.officials.unnamed"),
          })}
          note={t("floor.setup.officials.reserveNote")}
          serves={open.serves}
          disciplines={disciplines}
          onChange={(serves) => patch(editing, { serves })}
          onClose={() => setEditing(null)}
        />
      )}
    </SectionCard>
  );
}
