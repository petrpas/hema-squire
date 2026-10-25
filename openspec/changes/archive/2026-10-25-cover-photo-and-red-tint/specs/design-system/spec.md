## ADDED Requirements

### Requirement: A fourth pastel tint
`tokens.css` SHALL define a fourth pastel pair, `--ledger-red` and `--ledger-red-ink`, beside file-blue, seal-green and form-yellow, in the day skin and again in the night skin. It is a pastel like its siblings and SHALL NOT count as a second saturated color: `--stamp` remains the only one (`Global prohibitions`).

`--ledger-red` SHALL be told apart from `--stamp-tint` at a glance in both skins, because the open status block stands on `--stamp-tint` at the top left of a cover that may wear `--ledger-red`: it SHALL lean toward rose-brown where `--stamp-tint` leans pink. Because two pastels this close cannot be held apart by lightness alone in the night skin, on a cover wearing `--ledger-red` the open status block SHALL also be outlined 1px in `--stamp`, an outline and not a shadow. `--ledger-red-ink` SHALL reach at least 4.5:1 on `--ledger-red` in both skins.

The pair SHALL be used only as a cover tint and its Setup swatch; tags, faces and statuses keep the three original tints.

#### Scenario: Open status on a red cover
- **WHEN** a tournament whose cover wears the ledger-red tint has registration open
- **THEN** its status block on `--stamp-tint` is outlined 1px in `--stamp` and stands apart from the band around it, in the day skin and in the night skin

#### Scenario: Token audit
- **WHEN** the codebase is searched for the red tint's color values
- **THEN** they appear only in `tokens.css`
