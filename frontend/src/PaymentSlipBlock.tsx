import { useState } from "react";
import { useTranslation } from "react-i18next";

import CopyButton from "./CopyButton";

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

function CopyableField({ field }: { field: SlipField }) {
  const { t } = useTranslation();

  return (
    <div className="param-field">
      <span>{field.label}</span>
      <div className="slip-value-row">
        <strong className="data-value">{field.shown}</strong>
        {field.copy !== undefined && (
          <CopyButton value={field.copy} label={t("common.copy")} done={t("common.copied")} />
        )}
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
    <button
      type="button"
      className="secondary slip-save-qr"
      onClick={() => void save()}
      disabled={busy}
    >
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
      {/* the code and the button that saves it are one thing, stacked: the
          action belongs under what it acts on, not beside it */}
      <div className="payment-qr-block">
        <img className="payment-qr" src={`data:image/png;base64,${qrBase64}`} alt={qrAlt} />
        <div className="payment-slip-actions">
          <SaveQr base64={qrBase64} filename={qrFilename} />
        </div>
      </div>
      <div className="param-fields">
        {fields.map((field) => (
          <CopyableField key={field.key} field={field} />
        ))}
      </div>
    </div>
  );
}
