import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

/** Every dialog in Squire is the native `dialog` element, opened modally.
 *
 *  A div wearing a click handler has to reimplement what the element already
 *  is: the top layer, dismissal on Escape, focus held inside the dialog while
 *  it is open and returned to the opener when it closes, and a real `dialog`
 *  role for anything reading the page aloud. None of that was there before,
 *  and each piece of it is what a keyboard reaches the dialog with.
 *
 *  The element stays a two-part shape — the dialog is the centring frame the
 *  old backdrop div was, the content sits in the child — so that a click can
 *  be told apart from a click on the frame around it, and so the dialog's own
 *  padding is not a dismissal target. The dim is `::backdrop`.
 */
export default function Modal({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);

  // The contents are held back for the one render it takes to open, because
  // opening a dialog clears the page's focus first. A field that React had
  // already focused for its `autoFocus` would be blurred by that and arrive
  // showing the error for the value it has not been given yet. Nothing is
  // painted in between: a layout effect runs, and the render it schedules
  // completes, before the browser draws either state.
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (dialog === null || dialog.open) return;
    dialog.showModal();
    setOpen(true);
    return () => dialog.close();
  }, []);

  return (
    // The rule looks for onKeyDown/onKeyUp beside an onClick. The keyboard
    // equivalent of a click on the frame is Escape, which the element delivers
    // as `cancel` below, and the rule cannot see that.
    // biome-ignore lint/a11y/useKeyWithClickEvents: Escape arrives as `cancel`, handled below
    <dialog
      ref={ref}
      className="modal-backdrop"
      // Escape reaches the dialog as `cancel`; the close is the caller's to
      // make, so that a dialog holding unsaved work can still refuse it.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      {open && children}
    </dialog>
  );
}
