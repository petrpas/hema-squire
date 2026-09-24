import { type ReactNode, useId } from "react";

/** A control that is its own hint marker: the hint box `HelpHint` draws opens
 *  on hovering or focusing the control itself, with no glyph beside it.
 *
 *  For the Export card's actions, several of which are icons alone — the word
 *  the icon stands for is the control's accessible name, and the box says what
 *  pressing it does. A marker beside each would be a second mark per control
 *  in a row of three. `children` receives the box's id, for the control's
 *  `aria-describedby`. */
export default function HintedAction({
  hint,
  children,
}: {
  hint: string;
  children: (hintId: string) => ReactNode;
}) {
  const hintId = useId();
  return (
    <span className="action-hint">
      {children(hintId)}
      <span role="tooltip" id={hintId} className="help-hint-box">
        {hint}
      </span>
    </span>
  );
}
