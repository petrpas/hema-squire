## MODIFIED Requirements

### Requirement: LLM matching to HEMA Ratings
Imported fencers without a confirmed hr_id SHALL be fuzzy-matched by an LLM
against the fighters index, tolerant of diacritics, nicknames, and
transliterations. Results SHALL surface for review in the Matching phase as one
of three machine verdicts, and organizer corrections SHALL persist as rules.

The three machine verdicts are:

- **found** — the profile agrees with the registration on every signal the
  system can check: the names carry the same **name key**, the nationality does
  not contradict, and that name key identifies exactly one fighter in the index.
  Nothing was judged, only looked up, and the row owes the organizer no work.
- **proposed** — a match the model reached by judgment: a differing spelling, a
  nickname, a transliteration, a name carrying a token the other does not, a
  contradicting field, or a name key that more than one fighter in the index
  answers to. The row owes the organizer a look.
- **no match** — the model found no profile it would stand behind.

A **name key** is a name reduced to its words, each folded so that diacritics
and case do not distinguish it, taken without regard to the order the words
appear in. Two names share a key when they carry the same words: *Jan Novák* and
*Novák Jan* are one person under two conventions, and the system SHALL treat
them as agreeing. Names differing by a word one carries and the other does not
SHALL NOT share a key — a name key is not a subset test.

The tier SHALL be derived by the system from the stored match decision and the
index, not taken from a confidence the model reports about itself, so that the
same decision always yields the same tier and the reason for it is legible in
the claim and evidence registers the organizer is already looking at. A club
that differs SHALL NOT by itself hold a match out of **found**; club spellings
vary too freely to carry that weight.

The two sides name a country in different vocabularies — a registration writes
an ISO code, the fighters index writes an English name — so nationalities SHALL
be resolved to the country they name before they are compared, and SHALL
contradict only where they resolve to different countries. Comparing the
spellings instead would make nearly every fencer registered from abroad look
like a disagreement. Where either spelling names no country the system can
identify, the nationalities SHALL NOT be held to contradict: failing to
interpret a spelling is not the fencer disagreeing with their profile, and the
row would show no reason for the demotion.

An ambiguous name key SHALL never read as **found**, however exactly it
matches: where the index holds more than one fighter under the same name key,
the choice among them is a judgment, and the organizer makes it. Ambiguity SHALL
be judged by the same key the agreement is judged by, so that two fighters
indexed as *Jan Novák* and *Novák Jan* count as the ambiguity they are.

Deriving the tier SHALL NOT require re-invoking the LLM: a decision already
stored SHALL take its tier on the next recomputation of the table.

#### Scenario: Transliterated name
- **WHEN** an imported fencer's name differs from their HR profile only by transliteration
- **THEN** the profile is proposed as a match candidate rather than reported as unmatched, and the row reads proposed

#### Scenario: Exact hit owes no work
- **WHEN** an imported fencer's name key is carried by exactly one indexed fighter and their nationality agrees
- **THEN** the row reads found and is not queued for the organizer's attention

#### Scenario: Differing club does not demote an exact hit
- **WHEN** an imported fencer's name key matches unambiguously but their registered club is spelled differently from the profile's
- **THEN** the row still reads found

#### Scenario: A code and a country name are one country
- **WHEN** an imported fencer registered as "PL" matches unambiguously to a profile the index records as "Poland"
- **THEN** the nationalities are found to agree and the row reads found

#### Scenario: An uninterpretable nationality demotes nothing
- **WHEN** either side spells a nationality the system cannot resolve to a country
- **THEN** the nationalities are not held to contradict, and the other signals decide the tier

#### Scenario: Surname-first registration
- **WHEN** an imported fencer is registered as "Novák Jan" and the matched profile reads "Jan Novák"
- **THEN** the row reads found, the reversed order not being a difference the organizer needs to adjudicate

#### Scenario: An extra given name is a difference
- **WHEN** an imported fencer's name carries a word the matched profile's does not
- **THEN** the names do not share a key and the row reads proposed

#### Scenario: Two fighters share a name key
- **WHEN** an imported fencer's name key is answered by more than one fighter in the index
- **THEN** the row reads proposed however exact the match, and the organizer chooses

#### Scenario: Existing decisions take a tier without a rerun
- **WHEN** the table is recomputed after the tiers are introduced, over match decisions stored before them
- **THEN** each stored decision takes its tier, and no LLM call is made
