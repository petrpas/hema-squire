import { getToken } from "../api";

/** Opens a print's PDF: fetched with the console's credential, shown as a
 *  blob in a new tab, since a link cannot carry the credential. */
export async function openPdf(url: string): Promise<void> {
  const token = getToken();
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) return;
  window.open(URL.createObjectURL(await response.blob()), "_blank", "noopener");
}
