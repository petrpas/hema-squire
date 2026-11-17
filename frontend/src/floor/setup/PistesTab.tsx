import { IconArrowDown, IconArrowUp, IconPencil, IconTrash } from "@tabler/icons-react";
import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import type { FloorDiscipline, FloorPiste } from "../floorApi";
import { ServesDialog, servesText } from "./ServesDialog";
import {
  FieldNote,
  SectionCard,
  type SectionProps,
  useDraft,
  useErrorText,
  useSectionSave,
} from "./shared";

/** The pistes in their display order: name and the
 *  disciplines each serves, regular or reserve (spec floor-setup, Pistes and
 *  their availability). A piste serving nothing stays free for the floor. */
export function PistesTab({
  slug,
  onSaved,
  onDirty,
  pistes,
  disciplines,
}: SectionProps & { pistes: FloorPiste[]; disciplines: FloorDiscipline[] }) {
  const { t } = useTranslation();
  const [draft, setDraft, dirty] = useDraft(pistes, "pistes", onDirty);
  const { errors, failed, saving, save } = useSectionSave(slug, "pistes", onSaved);
  const errorAt = useErrorText(errors);
  const [editing, setEditing] = useState<number | null>(null);
  const open = editing === null ? undefined : draft[editing];

  function patch(index: number, fields: Partial<FloorPiste>) {
    setDraft(draft.map((piste, i) => (i === index ? { ...piste, ...fields } : piste)));
  }

  function move(index: number, by: -1 | 1) {
    const other = index + by;
    const a = draft[index];
    const b = draft[other];
    if (a === undefined || b === undefined) return;
    const next = [...draft];
    next[index] = b;
    next[other] = a;
    setDraft(next);
  }

  const free = draft.filter((piste) => piste.serves.length === 0).map((piste) => piste.name);
  const unserved = disciplines.filter(
    (d) => !draft.some((p) => p.serves.some((s) => s.discipline_id === d.id && !s.reserve)),
  );

  return (
    <SectionCard
      title={t("floor.setup.pistes.title")}
      hideTitle
      dirty={dirty}
      saving={saving}
      failed={failed}
      onSave={() => void save(draft)}
    >
      <div className="floor-days-scroll">
        <table className="sheet-table floor-pistes">
          {/* fixed columns; what is left goes to the disciplines */}
          <colgroup>
            <col className="floor-pistes-name" />
            <col />
            <col className="floor-pistes-actions" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">{t("floor.setup.pistes.name")}</th>
              <th scope="col">{t("floor.setup.pistes.disciplines")}</th>
              <th scope="col">
                <span className="visually-hidden">{t("floor.setup.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {draft.map((piste, index) => (
              <tr key={piste.id ?? `new-${index}`}>
                <td>
                  <input
                    value={piste.name}
                    maxLength={80}
                    aria-label={t("floor.setup.pistes.name")}
                    onChange={(event) => patch(index, { name: event.target.value })}
                  />
                  <FieldNote text={errorAt(`${index}.name`)} />
                </td>
                <td className="floor-days-text">
                  {servesText(
                    piste.serves,
                    disciplines,
                    t("floor.setup.serves.reserve"),
                    t("floor.setup.pistes.free"),
                  )}
                  <FieldNote text={errorAt(`${index}.serves.0`)} />
                </td>
                <td>
                  <div className="row-actions">
                    <RowIcon label={t("floor.setup.edit")} onClick={() => setEditing(index)}>
                      <IconPencil size={16} stroke={1.5} aria-hidden="true" />
                    </RowIcon>
                    <RowIcon
                      label={t("floor.setup.pistes.moveUp")}
                      disabled={index === 0}
                      onClick={() => move(index, -1)}
                    >
                      <IconArrowUp size={16} stroke={1.5} aria-hidden="true" />
                    </RowIcon>
                    <RowIcon
                      label={t("floor.setup.moveDown")}
                      disabled={index === draft.length - 1}
                      onClick={() => move(index, 1)}
                    >
                      <IconArrowDown size={16} stroke={1.5} aria-hidden="true" />
                    </RowIcon>
                    <RowIcon
                      label={t("floor.setup.pistes.remove")}
                      onClick={() => setDraft(draft.filter((_, i) => i !== index))}
                    >
                      <IconTrash size={16} stroke={1.5} aria-hidden="true" />
                    </RowIcon>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {free.length > 0 && (
        <p className="muted">{t("floor.setup.pistes.freeNote", { names: free.join(", ") })}</p>
      )}
      {unserved.length > 0 && (
        <p className="floor-missing">
          {t("floor.setup.pistes.unserved", { names: unserved.map((d) => d.name).join(", ") })}
        </p>
      )}
      <button
        type="button"
        className="secondary"
        onClick={() =>
          setDraft([
            ...draft,
            {
              id: null,
              name: String(draft.length + 1),
              serves: disciplines.map((d) => ({ discipline_id: d.id, reserve: false })),
            },
          ])
        }
      >
        {t("floor.setup.pistes.add")}
      </button>
      {open !== undefined && editing !== null && (
        <ServesDialog
          title={t("floor.setup.pistes.servesTitle", { name: open.name })}
          note={t("floor.setup.pistes.reserveNote")}
          serves={open.serves}
          disciplines={disciplines}
          onChange={(serves) => patch(editing, { serves })}
          onClose={() => setEditing(null)}
        />
      )}
    </SectionCard>
  );
}

/** An icon button of a row, named for a screen reader and on hover. */
function RowIcon({
  label,
  disabled = false,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="row-action"
      title={label}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
      <span className="visually-hidden">{label}</span>
    </button>
  );
}
