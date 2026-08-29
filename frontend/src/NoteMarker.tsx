import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

/** A row's note or its parse problems: a marker where there is something to
 *  read, and nothing at all where there is not (spec `etl-console`, Note and
 *  problem markers).
 *
 *  The text is disclosed in place and read-only — a note is the fencer's words
 *  or the parser's, a problem is the parser's report, and neither is the
 *  organizer's to rewrite. Opening is a click or a keypress, not a hover: this
 *  is content to read, not a hint to glance at, and a marker reachable only by
 *  pointer would put a parse doubt out of reach of the keyboard. */
export default function NoteMarker({
  kind,
  text,
}: {
  kind: "note" | "problem";
  text: string;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    function outside(event: MouseEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", dismiss);
    document.addEventListener("mousedown", outside);
    return () => {
      document.removeEventListener("keydown", dismiss);
      document.removeEventListener("mousedown", outside);
    };
  }, [open]);

  const label = t(`marker.${kind}`);
  return (
    <span className="note-marker" ref={wrapper}>
      <button
        type="button"
        className={`note-marker-button note-marker-${kind}`}
        aria-expanded={open}
        aria-label={label}
        title={label}
        onClick={() => setOpen((was) => !was)}
      >
        {kind === "note" ? "[i]" : "[!]"}
      </button>
      {open && (
        <span className="note-marker-panel">
          <span className="note-marker-label">{label}</span>
          <span className="note-marker-text">{text}</span>
        </span>
      )}
    </span>
  );
}
