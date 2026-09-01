import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

/** One transfer detail: its label, the value as the fencer must enter it into
 *  their bank, and — where the value has to be typed by hand — whether it can
 *  be copied. `copy` carries the plain string to place on the clipboard, which
 *  is not always what is displayed (an amount is shown grouped and with its
 *  unit; what belongs in a payment form is the bare number). */
export type SlipField = {
  key: string;
  label: string;
  shown: string;
  copy?: string;
};

/** Whether this browser exposes a clipboard at all.
 *
 *  `navigator.clipboard` is only present in a secure context: it is there on
 *  hemasquire.eu and on localhost, and absent over a LAN IP — which is exactly
 *  how a phone is usually pointed at a dev server. The control is rendered
 *  from this check rather than assumed, so where copying cannot work no button
 *  is offered, instead of one that fails silently when pressed. */
function clipboardAvailable(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.clipboard?.writeText === "function";
}

function CopyableField({ field }: { field: SlipField }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current !== null) clearTimeout(timer.current);
  }, []);

  const offered = field.copy !== undefined && clipboardAvailable();

  async function copy() {
    if (field.copy === undefined) return;
    try {
      await navigator.clipboard.writeText(field.copy);
    } catch {
      // The clipboard can still refuse — a permission policy, a page that lost
      // focus. Saying nothing is right: the value is on screen and readable,
      // and an error banner over a payment slip reads as a payment problem.
      return;
    }
    setCopied(true);
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 2400);
  }

  return (
    <div className="param-field">
      <span>{field.label}</span>
      <div className="slip-value-row">
        <strong className="data-value">{field.shown}</strong>
        {offered && (
          <button type="button" className="link-button slip-copy" onClick={() => void copy()}>
            {t("payment.copy")}
          </button>
        )}
        {/* Static note, and it leaves by fading out — the design admits a
            fade-out departure and nothing else. No toast, no icon swap. */}
        <span className={copied ? "slip-copied is-shown" : "slip-copied"} aria-live="polite">
          {copied ? t("payment.copied") : ""}
        </span>
      </div>
    </div>
  );
}

/** Hands the QR image to the device.
 *
 *  The whole SPAYD flow assumes two devices — the code on a screen, a phone in
 *  hand. On one device the code is inert, and this is what replaces it.
 *
 *  Share first, download second. On iOS a plain `<a download>` writes into the
 *  Files app, and the Czech banking applications that read a QR from an image
 *  read it from the photo library; the share sheet is what reaches the photo
 *  library, and it can also hand the image straight to the bank's own app. The
 *  download is the fallback for desktop browsers with no share sheet, where it
 *  is the right behaviour anyway. */
function SaveQr({ base64, filename }: { base64: string; filename: string }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);

  function toBlob(): Blob {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: "image/png" });
  }

  function download(blob: Blob) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function save() {
    setBusy(true);
    try {
      const blob = toBlob();
      const file = new File([blob], filename, { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file] });
          return;
        } catch (err) {
          // A dismissed share sheet is the fencer changing their mind, not a
          // failure to recover from with a surprise download.
          if (err instanceof DOMException && err.name === "AbortError") return;
        }
      }
      download(blob);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button type="button" className="secondary slip-save-qr" onClick={() => void save()} disabled={busy}>
      {t("payment.saveQr")}
    </button>
  );
}

/** The payment slip's body: the QR, the actions that make it usable on the
 *  device showing it, and the transfer details.
 *
 *  Written once and given a field list rather than fixed slots, because the
 *  two currency branches genuinely differ — the EUR one carries no domestic
 *  account number and quotes a message where the local one quotes a VS. */
export default function PaymentSlipBlock({
  fields,
  qrBase64,
  qrAlt,
  qrFilename,
}: {
  fields: SlipField[];
  qrBase64: string;
  qrAlt: string;
  qrFilename: string;
}) {
  return (
    <div className="payment-block">
      <img className="payment-qr" src={`data:image/png;base64,${qrBase64}`} alt={qrAlt} />
      <div className="payment-slip-actions">
        <SaveQr base64={qrBase64} filename={qrFilename} />
      </div>
      <div className="param-fields">
        {fields.map((field) => (
          <CopyableField key={field.key} field={field} />
        ))}
      </div>
    </div>
  );
}
