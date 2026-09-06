import { useId } from "react";

// Static hover/focus marker for fields whose expected content is not evident
// from the label (design D3). Never an emoji, never filled: a bordered glyph.
//
// Deliberately not a <button>. Every call site sits inside the field's own
// <label>, and a button is a labelable element: as the first labelable
// descendant it became the label's labeled control, so the browser mirrored
// the label's :hover onto it and the hint opened whenever the pointer crossed
// the field itself — and a click on the label focused the marker instead of
// the input. A <span> is not labelable, which leaves the field as the label's
// control and the hint on the glyph alone. It carries tabindex so the box
// still opens from the keyboard; the marker has no action to invoke.
export default function HelpHint({
  text,
  align = "left",
}: {
  text: string;
  /** Where the box hangs from the marker. "left" opens rightward from the
   *  marker's own left edge, which is right for a marker leading a row. Pass
   *  "center" where the marker sits mid-row instead — trailing a heading, say
   *  — and a leftward box would reach out of its container. */
  align?: "left" | "center";
}) {
  const hintId = useId();
  return (
    <span className={align === "center" ? "help-hint help-hint-center" : "help-hint"}>
      <span className="help-hint-marker" tabIndex={0} aria-describedby={hintId}>
        i
      </span>
      <span role="tooltip" id={hintId} className="help-hint-box">
        {text}
      </span>
    </span>
  );
}
