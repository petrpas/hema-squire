import { type RefObject, useEffect, useRef } from "react";

/** Keeps the selected tab visible inside a scrolling `.stage-control-band`.
 *
 *  Without it the band simply starts at its first tab: a fencer whose filter
 *  is "Mine" opens the page, sees "Announced" and "Open", and has no way of
 *  knowing which one is selected — the marker is off-screen to the right.
 *
 *  `block: "nearest"` matters as much as `inline: "center"`. Centring a tab
 *  horizontally will otherwise also centre it vertically, which scrolls the
 *  whole document to put the top bar mid-screen and jumps the workspace out
 *  from under the reader on every tab change.
 *
 *  Returns the ref to put on the band element. */
export function useTabBand(activeKey: string): RefObject<HTMLElement> {
  const band = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = band.current;
    if (el === null) return;
    // only while the band actually scrolls — above 768px it does not, and
    // scrolling a non-overflowing element into view is a no-op we can skip
    if (el.scrollWidth <= el.clientWidth) return;
    const active = el.querySelector(".active, [aria-selected='true']");
    active?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [activeKey]);

  return band;
}
