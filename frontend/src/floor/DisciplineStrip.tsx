import { type KeyboardEvent, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import * as routes from "../routes";
import type { FloorTab } from "./tabs";

/** A step tab's disciplines as a strip of tabs at the head of the work, in
 *  floor Setup's order, never a drop-down (spec floor-console, Step tabs
 *  choose their discipline by tabs). Prezence leads with "Všichni", which is
 *  its address without a discipline. Left and right move along it; it
 *  scrolls sideways within itself where the names do not fit. */
export function DisciplineStrip({
  slug,
  tab,
  disciplines,
  current,
  all = false,
}: {
  slug: string;
  tab: FloorTab;
  disciplines: { slug: string; name: string }[];
  /** The current discipline's slug; null is "Všichni". */
  current: string | null;
  all?: boolean;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const list = useRef<HTMLDivElement>(null);
  const items: { slug: string | null; name: string }[] = [
    ...(all ? [{ slug: null, name: t("floor.ops.all") }] : []),
    ...disciplines,
  ];

  function go(target: string | null) {
    navigate(routes.floorPath(slug, tab, target ?? undefined));
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const nextIndex = (index + step + items.length) % items.length;
    const next = items[nextIndex];
    if (next === undefined) return;
    go(next.slug);
    list.current?.querySelectorAll<HTMLButtonElement>("button")[nextIndex]?.focus();
  }

  return (
    <div
      ref={list}
      className="floor-strip"
      role="tablist"
      aria-orientation="horizontal"
      aria-label={t("floor.ops.disciplines")}
    >
      {items.map((item, index) => {
        const selected = item.slug === current;
        return (
          <button
            key={item.slug ?? ""}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={selected ? "active" : ""}
            onClick={() => go(item.slug)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {item.name}
          </button>
        );
      })}
    </div>
  );
}
