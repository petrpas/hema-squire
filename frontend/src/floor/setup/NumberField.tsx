import { FieldNote, wholeNumber } from "./shared";

/** A labelled whole number of a format, with its field's error. */
export function NumberField({
  label,
  value,
  min,
  max,
  error,
  disabled = false,
  onChange,
}: {
  label: string;
  value: number | null;
  min: number;
  max: number;
  error: string | null;
  disabled?: boolean;
  /** null while the field is empty */
  onChange: (value: number | null) => void;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => onChange(wholeNumber(event.target.value))}
      />
      <FieldNote text={error} />
    </label>
  );
}
