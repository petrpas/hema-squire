/** Which bank an account belongs to, read from the value the organizer is
 *  typing rather than from the one the server has stored.
 *
 *  This is the console's only piece of account knowledge, and it answers one
 *  question: is this a Fio account. Squire polls Fio's API and no other bank's,
 *  so a bank feed token means nothing anywhere else, and the control that
 *  records one is offered only where it does (spec tournament-admin).
 *
 *  The backend holds no counterpart. It has nothing to gate on: a token may be
 *  recorded while the account beside it is still unsaved, so the endpoint
 *  cannot check the token against a stored account. The rule is about which
 *  control is offered, so it lives where the controls are.
 */

// Fio banka: CZ and SK
const FIO_BANK_CODES = new Set(["2010", "8330"]);

// the two forms the account field accepts, as `app/accounts.py` parses them
const IBAN = /^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$/;
const DOMESTIC = /^(?:[0-9]{1,6}-)?[0-9]{2,10}\/([0-9]{4})$/;

/** The account's bank code, or null where the value is not yet a whole
 *  account. Deliberately no validation: a checksum that does not agree is the
 *  field's own error to report, and a second error about one value teaches
 *  nothing. */
export function bankCode(raw: string): string | null {
  const value = raw.trim().replace(/\s+/g, "").toUpperCase();
  const domestic = DOMESTIC.exec(value);
  if (domestic) return domestic[1];
  // in an IBAN the bank code is the first four characters of the BBAN, in both
  // countries Fio operates in
  if (IBAN.test(value)) return value.slice(4, 8);
  return null;
}

export function isFioAccount(raw: string): boolean {
  const code = bankCode(raw);
  return code !== null && FIO_BANK_CODES.has(code);
}
