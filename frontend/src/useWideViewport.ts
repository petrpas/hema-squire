import { useState } from "react";

/** Whether this is a screen wide enough to focus a field on arrival, and to
 *  keep the HR picker inline rather than lifting it onto its own step.
 *
 *  Read once, at mount, rather than on every render. On a phone an automatic
 *  focus raises the keyboard over the form and pushes its heading and first
 *  fields out of view before they can be read; and re-reading the width per
 *  render would let the answer change under a fencer mid-typing — a rotating
 *  phone, or the keyboard itself resizing the viewport — moving the picker
 *  they were using out from under them.
 *
 *  768px is the canonical middle breakpoint (see tokens.css). */
export function useWideViewport(): boolean {
  const [wide] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(min-width: 768px)").matches,
  );
  return wide;
}
