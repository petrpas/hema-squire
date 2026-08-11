## ADDED Requirements

### Requirement: Bank account entry and storage
The bank account SHALL be accepted in either of two forms: an IBAN, or the Czech domestic form `[prefix-]number/bankcode` with a prefix of up to six digits that MAY be omitted, an account number of two to ten digits, and a four-digit bank code. An organizer SHALL NOT be required to look up an IBAN to configure a Czech tournament, because the domestic form is the one printed on statements and used in domestic transfers, while the IBAN appears in neither.

A Czech account entered in domestic form SHALL be converted to its IBAN and stored as that IBAN, so that the stored value is always canonical and every consumer of the account sees exactly one format. The conversion SHALL be the standard mapping — bank code, then the prefix padded to six digits, then the account number padded to ten — with check digits computed rather than supplied. No second form SHALL be stored, since the domestic form is recoverable from a Czech IBAN whenever it is needed.

The account SHALL be validated, not merely shape-checked. An IBAN SHALL satisfy its mod-97 check digits. A Czech account entered in domestic form SHALL satisfy the weighted modulo-11 checksum on its prefix and on its account number independently, both of which every genuine Czech account satisfies. An account failing either check SHALL be refused with a message naming the check that failed, rather than being stored, printed into payment emails, and encoded into a QR code that fails at the payer's bank. The bank code SHALL be checked for shape only and SHALL NOT be validated against a registry of live codes, which would rot.

Only the Czech domestic form SHALL be accepted alongside IBAN. An account in any other country SHALL be entered as its IBAN.

An account stored before this validation existed SHALL NOT be re-validated or rejected on read, and SHALL continue to be used exactly as it is.

#### Scenario: Domestic account accepted and stored as IBAN
- **WHEN** the organizer saves the bank account as `19-2000145399/0800`
- **THEN** the save succeeds and the stored value is the corresponding IBAN

#### Scenario: Domestic account without a prefix
- **WHEN** the organizer saves an account with no prefix, as `2000145399/0800`
- **THEN** it is accepted and converted with a zero prefix

#### Scenario: IBAN accepted unchanged
- **WHEN** the organizer saves a valid IBAN
- **THEN** it is stored as given, normalized only for spacing and case

#### Scenario: Both forms of one account are the same account
- **WHEN** the organizer saves an account in domestic form, and later saves the IBAN that account converts to
- **THEN** the stored value is identical in both cases

#### Scenario: Mistyped IBAN refused
- **WHEN** the organizer saves an IBAN whose check digits do not agree with the rest of the value
- **THEN** the save is refused, naming the failed check, and nothing is stored

#### Scenario: Mistyped domestic account refused
- **WHEN** the organizer saves a domestic account whose account number fails the modulo-11 checksum
- **THEN** the save is refused, naming the failed check, and nothing is stored

#### Scenario: Foreign account entered as IBAN
- **WHEN** the organizer of a tournament banking outside Czechia saves that account as an IBAN
- **THEN** it is accepted, and no domestic form is required or derived

#### Scenario: Existing account is left alone
- **WHEN** a tournament whose account was stored before this validation is loaded and used to build payment instructions
- **THEN** the account is used as stored and no validation refuses it
