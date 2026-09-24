import { IconCopy } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";

/** Whether this browser exposes a clipboard at all.
 *
 *  `navigator.clipboard` is only present in a secure context: it is there on
 *  hemasquire.eu and on localhost, and absent over a LAN IP — which is exactly
 *  how a phone is usually pointed at a dev server. A control is rendered from
 *  this check rather than assumed, so where copying cannot work no button is
 *  offered, instead of one that fails silently when pressed. */
export function clipboardAvailable(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.clipboard?.writeText === "function";
}

/** One value's copy action: the glyph, and the static note that says it
 *  happened.
 *
 *  The action names itself by its glyph — it sits beside a value, and a word
 *  there would compete with the value for the eye. Outline, never filled. The
 *  note appears at once and leaves by fading out, which is the one departure
 *  the design admits: no toast, no icon swap.
 *
 *  Renders nothing where the browser has no clipboard. Labels arrive as props
 *  rather than being read from one place in the catalogue, because what is
 *  being copied differs by caller and the title is what says which. */
export default function CopyButton({
  value,
  label,
  done,
}: {
  value: string;
  label: string;
  done: string;
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );

  if (!clipboardAvailable()) return null;

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // The clipboard can still refuse — a permission policy, a page that lost
      // focus. Saying nothing is right: the value is on screen and readable,
      // and an error banner over it reads as a problem with the value.
      return;
    }
    setCopied(true);
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 2400);
  }

  return (
    <>
      <button
        type="button"
        className="row-action slip-copy"
        title={label}
        aria-label={label}
        onClick={() => void copy()}
      >
        <IconCopy size={16} stroke={1.5} />
      </button>
      <span className={copied ? "slip-copied is-shown" : "slip-copied"} aria-live="polite">
        {copied ? done : ""}
      </span>
    </>
  );
}
