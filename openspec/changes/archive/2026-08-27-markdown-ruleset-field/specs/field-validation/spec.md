## MODIFIED Requirements

### Requirement: URL fields are parsed and scheme-restricted
Every field holding a link SHALL be parsed as a URL and SHALL be accepted only with an `http` or `https` scheme. `javascript:`, `data:` and other schemes SHALL be rejected at validation, not filtered at render time. A value that does not parse as a URL SHALL be rejected with a malformed-link error. This governs fields submitted as a URL of their own. A link written inside a markdown field is not such a field — it is part of prose, is stored verbatim as the organizer typed it, and is governed instead by the render-time sanitizer `organizer-prose` requires.

#### Scenario: A script URL in an organizer link
- **WHEN** a `javascript:` URL is submitted as a titular organizer's link
- **THEN** the request is rejected with a link-scheme error and the value is never stored

#### Scenario: A script URL in a ruleset link
- **WHEN** `[click](javascript:alert(1))` is submitted as a discipline's ruleset
- **THEN** the value is stored as typed, because the ruleset is prose rather than a URL field, and nothing carrying that destination reaches the document when it is presented

#### Scenario: A link without a scheme
- **WHEN** `example.com/rules` is submitted as a link
- **THEN** the organizer is told the link must begin with `http://` or `https://`
