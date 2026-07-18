import { useEffect, useRef, useState } from "react";

export default function EditableCell({
  display,
  value,
  onSave,
}: {
  display: React.ReactNode;
  value: unknown;
  onSave: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  if (!editing) {
    return (
      <div
        className="cell-editable"
        onDoubleClick={() => {
          setDraft(value === null || value === undefined ? "" : String(value));
          setEditing(true);
        }}
      >
        {display}
      </div>
    );
  }

  function commit() {
    setEditing(false);
    const original = value === null || value === undefined ? "" : String(value);
    if (draft !== original) onSave(draft);
  }

  return (
    <input
      ref={inputRef}
      className="cell-input"
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") commit();
        if (event.key === "Escape") setEditing(false);
      }}
    />
  );
}
