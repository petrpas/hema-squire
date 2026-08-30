import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { DedupGroup as Group } from "../api";
import { IDENTITY_COLUMNS, identityValue } from "../identity";
import { registeredMoment } from "../momentText";
import NoteMarker from "../NoteMarker";
import ConclusionRow from "./ConclusionRow";
import { GROUP_COLUMNS, asList } from "./mergeFields";

/** One candidate duplicate group: the records, and the record a merge would
 *  make of them.
 *
 *  The whole ledger line is here, in one table — the claim and the evidence in
 *  the member rows, the verdict beneath them under a rule — so that what a
 *  merge would keep and what it would drop are read down one column rather than
 *  described (spec `etl-console`, Deduplication candidate review).
 */

const TAGS: Record<string, string> = {
  merged: "tag tag-seal-green",
  pending: "tag tag-form-yellow",
};

export default function DedupGroup({
  group,
  timezone,
  onDecide,
}: {
  group: Group;
  timezone: string | null;
  onDecide: (accept: boolean, fields?: Record<string, unknown>, note?: string) => void;
}) {
  const { t } = useTranslation();
  const settled = group.verdict !== "pending";
  const standing = group.conclusion ?? group.recommendation;
  const [editing, setEditing] = useState(false);
  const [fields, setFields] = useState<Record<string, unknown>>(standing.fields);
  const [note, setNote] = useState(standing.note);

  // the draft is the group's own, discarded when it leaves (design D5)
  const open = !settled || editing;

  function reopen() {
    setFields(standing.fields);
    setNote(standing.note);
    setEditing(true);
  }

  function confirm() {
    setEditing(false);
    onDecide(true, fields, note);
  }

  function separate() {
    setEditing(false);
    onDecide(false);
  }

  const shared = group.members.find((member) => member.hr_id !== null)?.hr_id ?? null;

  return (
    <section className="dedup-group">
      <div className="dedup-group-head">
        <h2>
          {t(`dedup.kind.${group.kind}`)}
          {group.kind === "same_id" && shared !== null && (
            <span className="dedup-group-evidence"> · {t("column.hr_id")} {shared}</span>
          )}
        </h2>
        <span className="dedup-verdict">
          {TAGS[group.verdict] ? (
            <span className={TAGS[group.verdict]}>{t(`dedup.verdict.${group.verdict}`)}</span>
          ) : (
            <span className="state-text">{t(`dedup.verdict.${group.verdict}`)}</span>
          )}
          {group.decided_by !== null && (
            <span className="dedup-decided-by">{t(`dedup.by.${group.decided_by}`)}</span>
          )}
        </span>
      </div>

      <table className="sheet-table dedup-table">
        <thead>
          <tr>
            <th className="col-index">#</th>
            {GROUP_COLUMNS.map((column) => (
              <th key={column} className={column === "notes" ? "col-marker" : ""}>
                {t(`column.${column}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {group.members.map((member) => (
            <tr key={member.id}>
              <td className="col-index">{member.number ?? "—"}</td>
              {GROUP_COLUMNS.map((column) => {
                if (IDENTITY_COLUMNS.includes(column)) {
                  const { text, declared } = identityValue(member, column, true);
                  return (
                    <td key={column}>
                      {declared ? <span className="identity-declared">{text}</span> : text}
                    </td>
                  );
                }
                if (column === "notes") {
                  const value = member.notes;
                  return (
                    <td key={column} className="col-marker">
                      {value && value.trim() !== "" ? (
                        <NoteMarker kind="note" text={value} />
                      ) : null}
                    </td>
                  );
                }
                if (column === "registered_at") {
                  return <td key={column}>{registeredMoment(member.registered_at, timezone)}</td>;
                }
                if (column === "disciplines" || column === "weapon_rentals") {
                  const values = asList(member[column]);
                  return <td key={column}>{values.length > 0 ? values.join(", ") : "—"}</td>;
                }
                if (column === "afterparty") {
                  return <td key={column}>{member.afterparty ? "✓" : "—"}</td>;
                }
                const value = member[column];
                return (
                  <td key={column}>
                    {value === null || value === undefined || value === "" ? "—" : String(value)}
                  </td>
                );
              })}
            </tr>
          ))}
          <ConclusionRow
            fields={open ? fields : standing.fields}
            note={open ? note : standing.note}
            members={group.members}
            editable={open}
            timezone={timezone}
            onField={(column, value) => setFields((was) => ({ ...was, [column]: value }))}
            onNote={setNote}
          />
        </tbody>
      </table>

      {/* one action reaches the opposite verdict, whatever verdict stands
          (spec etl-console, A settled group can be decided again) */}
      <div className="dedup-actions">
        {open ? (
          <>
            <button className="secondary" onClick={confirm}>
              {t("dedup.accept")}
            </button>
            <button className="row-action" onClick={separate}>
              {t("dedup.reject")}
            </button>
          </>
        ) : group.verdict === "merged" ? (
          <>
            <button className="row-action" onClick={separate}>
              {t("dedup.reject")}
            </button>
            <button className="row-action" onClick={reopen}>
              {t("dedup.reopen")}
            </button>
          </>
        ) : (
          <button className="secondary" onClick={() => onDecide(true)}>
            {t("dedup.accept")}
          </button>
        )}
      </div>
    </section>
  );
}
