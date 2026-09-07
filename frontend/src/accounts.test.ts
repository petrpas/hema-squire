import { describe, expect, it } from "vitest";

import { isFioAccount } from "./accounts";

// the same Fio account written both ways the field accepts
const FIO_IBAN = "CZ8620100000002900123456";
const FIO_DOMESTIC = "2900123456/2010";

describe("isFioAccount", () => {
  it("recognises a Fio account in either form", () => {
    expect(isFioAccount(FIO_IBAN)).toBe(true);
    expect(isFioAccount(FIO_DOMESTIC)).toBe(true);
  });

  it("reads an IBAN however it is spaced or cased", () => {
    expect(isFioAccount("cz86 2010 0000 0029 0012 3456")).toBe(true);
  });

  it("recognises the Slovak Fio bank code", () => {
    expect(isFioAccount("SK9783300000002900123456")).toBe(true);
  });

  it("says no to another bank in either form", () => {
    expect(isFioAccount("CZ6508000000192000145399")).toBe(false);
    expect(isFioAccount("19-2000145399/0800")).toBe(false);
  });

  it("says no to a value that is not yet a whole account", () => {
    expect(isFioAccount("")).toBe(false);
    expect(isFioAccount("   ")).toBe(false);
    expect(isFioAccount("CZ46201")).toBe(false);
    expect(isFioAccount("2900123456/")).toBe(false);
  });

  it("answers on the bank code alone, leaving the checksum to the field", () => {
    // a Fio bank code whose check digits do not agree: the control is offered,
    // and the account field reports its own error
    expect(isFioAccount("CZ0020100000002900123456")).toBe(true);
  });
});
