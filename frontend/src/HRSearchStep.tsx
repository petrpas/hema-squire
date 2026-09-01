import { type ReactNode } from "react";

/** The HR picker lifted onto its own screen.
 *
 *  Below 768px the picker cannot stay inline: on a 390px screen the signup
 *  form grows past three screens with a search field and its results in the
 *  middle, and the fencer loses track of what they were filling in. This is
 *  the layer that holds it instead.
 *
 *  It deliberately renders no picker of its own — the caller passes one in.
 *  The two call sites configure `HRSearchPicker` differently (signup searches
 *  by the name held in its form and offers no query field; Profile offers its
 *  own, seeded from the display name), and flattening that difference here
 *  would mean reimplementing one of them.
 *
 *  Critically, this is a layer and not a route. It is rendered by the
 *  component that owns the form state, so nothing unmounts while it is open
 *  and every value entered survives the round trip. Navigating to a screen of
 *  its own would discard them. */
export default function HRSearchStep({
  title,
  subtitle,
  backLabel,
  onBack,
  children,
}: {
  title: string;
  /** What the step is searching for, where the picker has no query field of
   *  its own to say so. Without it the fencer meets a nationality control and
   *  a search button with nothing stating what is being searched. */
  subtitle?: string;
  backLabel: string;
  onBack: () => void;
  children: ReactNode;
}) {
  return (
    <div className="hr-step" role="dialog" aria-modal="true" aria-label={title}>
      <div className="hr-step-head">
        <h2>{title}</h2>
        {subtitle !== undefined && <p className="hr-step-subtitle">{subtitle}</p>}
      </div>
      <div className="hr-step-body">{children}</div>
      <div className="hr-step-foot">
        <button type="button" className="secondary" onClick={onBack}>
          {backLabel}
        </button>
      </div>
    </div>
  );
}
