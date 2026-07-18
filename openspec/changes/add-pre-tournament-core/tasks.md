# Tasks

## 1. Foundations
- [x] 1.1 Scaffold application (backend, frontend shell per wireframe B, CI)
- [x] 1.2 Multi-tenant data model: tournaments, fencers, registrations
- [x] 1.3 Localization infrastructure with complete CZ locale
- [ ] 1.4 hr-integration: fighters index download, cache, refresh, search

## 2. Accounts and registration
- [x] 2.1 Fencer account creation with HR binding flow (HR search stubbed until 1.4)
- [x] 2.2 Tournament administration: disciplines, capacity, pricing, parameters
- [x] 2.3 Registration flow: disciplines + extras, fee computation, reservation with VS
- [x] 2.4 Confirmation email with SPAYD QR (outbox/log mail backend; real provider TBD)
- [x] 2.5 Public participant list (paid-only visibility)

## 3. Payments
- [x] 3.1 Fio API ingestion and CSV statement import behind one idempotent interface
- [x] 3.2 VS matching with amount tolerance; unmatched queue
- [x] 3.3 Reminder and expiry scheduler; audited events
- [x] 3.4 Manual matching operation persisted as a rule

## 4. Console and rules engine
- [x] 4.1 edit-rules engine: rules, replay, removal, audit journal
- [x] 4.2 ETL console shell: phase stepper, sheet table, operations rail
- [x] 4.3 Phase views: columns, parameter panels, per-phase edits log
- [x] 4.4 Row operations: inline edit, reversible delete, match resolution

## 5. Import and export
- [x] 5.1 Table import: file intake, LLM parse, problems surfacing (Google Sheet intake arrives with the 5.4 Sheets client)
- [ ] 5.2 LLM HR matching and three-band dedup with decision persistence
- [ ] 5.3 Canonical JSON export (versioned schema)
- [ ] 5.4 Google Sheets export with preserve/refresh semantics

## 6. Validation
- [ ] 6.1 Determinism test: source + rules + params → identical state across reruns
- [ ] 6.2 Payment lifecycle end-to-end test (reserve → QR → match → paid; expiry path)
- [ ] 6.3 Pilot replay on a real tournament dataset (Na Duel! archive)
