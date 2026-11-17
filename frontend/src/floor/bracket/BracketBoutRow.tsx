import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { type BracketBout, bracketApi, type Outcome, type ResultIn } from "../floorApi";

/** One elimination bout: scores, or a walkover with its note. A winner is
 *  required; the winner advances on save (spec floor-bracket). */
export function BracketBoutRow({
  slug,
  discipline,
  bout,
  name,
  label,
  onChanged,
}: {
  slug: string;
  discipline: number;
  bout: BracketBout;
  name: (key: string) => string;
  label: string;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [a, setA] = useState(bout.score_a === null ? "" : String(bout.score_a));
  const [b, setB] = useState(bout.score_b === null ? "" : String(bout.score_b));
  const [walkover, setWalkover] = useState<"" | "a" | "b">("");
  const [note, setNote] = useState(bout.note ?? "");
  const [refusal, setRefusal] = useState<string | null>(null);

  function result(): ResultIn | null {
    const sa = Number.parseInt(a || "0", 10);
    const sb = Number.parseInt(b || "0", 10);
    if (Number.isNaN(sa) || Number.isNaN(sb)) return null;
    let outcomes: [Outcome, Outcome];
    if (walkover === "a") outcomes = ["no", "win"];
    else if (walkover === "b") outcomes = ["win", "no"];
    else if (sa === sb) return null;
    else outcomes = sa > sb ? ["win", "loss"] : ["loss", "win"];
    return {
      score_a: sa,
      score_b: sb,
      outcome_a: outcomes[0],
      outcome_b: outcomes[1],
      note: note.trim() || null,
      version: bout.version,
    };
  }

  async function save() {
    const value = result();
    if (value === null) {
      setRefusal("winner_required");
      return;
    }
    setRefusal(null);
    try {
      await bracketApi.record(slug, discipline, bout.id, value);
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      setRefusal(
        typeof detail === "string"
          ? detail
          : typeof detail === "object" && detail !== null && "reason" in detail
            ? String(detail.reason)
            : "failed",
      );
    }
    onChanged();
  }

  return (
    <li
      className={bout.score_a === null ? "floor-bracket-bout" : "floor-bracket-bout floor-recorded"}
    >
      <span className="muted">{label}</span>
      <span>{name(bout.a)}</span>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={99}
        aria-label={t("floor.pools.scoreOf", { name: name(bout.a) })}
        value={a}
        onChange={(event) => setA(event.target.value)}
      />
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={99}
        aria-label={t("floor.pools.scoreOf", { name: name(bout.b) })}
        value={b}
        onChange={(event) => setB(event.target.value)}
      />
      <span>{name(bout.b)}</span>
      <select
        aria-label={t("floor.bracket.walkover")}
        value={walkover}
        onChange={(event) =>
          setWalkover(event.target.value === "a" ? "a" : event.target.value === "b" ? "b" : "")
        }
      >
        <option value="">{t("floor.bracket.fenced")}</option>
        <option value="a">{t("floor.bracket.didNotFence", { name: name(bout.a) })}</option>
        <option value="b">{t("floor.bracket.didNotFence", { name: name(bout.b) })}</option>
      </select>
      {walkover !== "" && (
        <input
          aria-label={t("floor.bracket.note")}
          placeholder={t("floor.bracket.note")}
          value={note}
          maxLength={200}
          onChange={(event) => setNote(event.target.value)}
        />
      )}
      <button type="button" className="secondary" onClick={() => void save()}>
        {bout.score_a === null ? t("floor.ring.record") : t("floor.ring.correct")}
      </button>
      {refusal !== null && (
        <span className="floor-missing" role="alert">
          {t(`floor.bracket.refusals.${refusal}`, { defaultValue: t("floor.plan.failed") })}
        </span>
      )}
    </li>
  );
}
