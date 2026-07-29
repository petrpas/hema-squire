import { useId } from "react";

// Static hover/focus marker for fields whose expected content is not evident
// from the label (design D3). Never an emoji, never filled: a bordered glyph.
export default function HelpHint({ text }: { text: string }) {
  const hintId = useId();
  return (
    <span className="help-hint">
      <button type="button" className="help-hint-marker" aria-describedby={hintId}>
        i
      </button>
      <span role="tooltip" id={hintId} className="help-hint-box">
        {text}
      </span>
    </span>
  );
}
