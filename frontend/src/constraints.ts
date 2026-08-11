// Flat, literal-only mirror of backend/app/constraints.py and the bounds it
// feeds into backend/app/schemas.py. No imports, no expressions — every
// value here is a literal so backend/tests/test_constraints_mirror.py can
// parse this file as text and check it against what the backend actually
// publishes (design `add-field-validation` D1). Keyed "Model.field" after
// the pydantic model that carries the bound.
//
// A bound changed here without changing constraints.py (or the reverse)
// fails that test — do not hand-tune a number in only one of the two files.

export interface FieldConstraint {
  "minLength"?: number;
  "maxLength"?: number;
  "minimum"?: number;
  "maximum"?: number;
  "exclusiveMinimum"?: number;
  "exclusiveMaximum"?: number;
  "pattern"?: string;
  "enum"?: string[];
}

export const FIELD_CONSTRAINTS: Record<string, FieldConstraint> = {
  "SignupIn.password": { "minLength": 8 },
  "SignupIn.display_name": { "minLength": 1, "maxLength": 200 },
  "SignupIn.club": { "maxLength": 200 },
  "AccountUpdate.display_name": { "minLength": 1, "maxLength": 200 },
  "AccountUpdate.club": { "maxLength": 200 },
  "PleaIn.message": { "maxLength": 1000 },
  "DisciplineIn.slug": { "maxLength": 30, "pattern": "^[A-Za-z0-9-]{1,30}$" },
  "DisciplineIn.name": { "maxLength": 100 },
  "DisciplineIn.weapon": { "minLength": 1, "maxLength": 30 },
  "DisciplineIn.gender": { "enum": ["", "W", "M"] },
  "DisciplineIn.material": { "enum": ["", "Plastic"] },
  "DisciplineIn.kind": { "enum": ["individual", "team"] },
  "DisciplineIn.team_min": { "minimum": 1 },
  "DisciplineIn.team_max": { "minimum": 1 },
  "DisciplineIn.capacity": { "exclusiveMinimum": 0 },
  "DisciplineIn.fee": { "minimum": 0 },
  "DisciplineIn.fee_early": { "minimum": 0 },
  "DisciplineIn.fee_eur": { "minimum": 0, "maximum": 1000 },
  "DisciplineIn.fee_early_eur": { "minimum": 0, "maximum": 1000 },
  "DisciplineIn.schedule_when": { "maxLength": 200 },
  "DisciplineIn.schedule_where": { "maxLength": 300 },
  "DisciplineIn.ruleset_name": { "maxLength": 100 },
  "DisciplineIn.ruleset_url": { "maxLength": 500 },
  "ExtraItemIn.name": { "minLength": 1, "maxLength": 200 },
  "ExtraItemIn.price": { "minimum": 0 },
  "ExtraItemIn.price_eur": { "minimum": 0, "maximum": 1000 },
  "ExtraItemIn.max_qty": { "minimum": 1 },
  "ExtraItemIn.schedule_when": { "maxLength": 200 },
  "ExtraItemIn.schedule_where": { "maxLength": 300 },
  "ExtraItemIn.remark": { "maxLength": 500 },
  "ExtraItemIn.option_label": { "maxLength": 50 },
  "ExtraSelectionIn.qty": { "minimum": 1 },
  "ExtraSelectionIn.option_value": { "maxLength": 100 },
  "DiscountCondition.count": { "minimum": 1 },
  "DiscountEffect.value": { "minimum": 0 },
  "DiscountEffect.value_eur": { "minimum": 0, "maximum": 1000 },
  "DiscountIn.name": { "minLength": 1, "maxLength": 200 },
  "OrganizerIn.name": { "minLength": 1, "maxLength": 200 },
  "OrganizerIn.link": { "maxLength": 500 },
  "TournamentCreate.slug": { "pattern": "^[a-z0-9][a-z0-9-]{1,98}$" },
  "TournamentCreate.display_name": { "minLength": 1, "maxLength": 200 },
  "TournamentUpdate.display_name": { "minLength": 1, "maxLength": 200 },
  "TournamentUpdate.subtitle": { "maxLength": 400 },
  "TournamentUpdate.location": { "maxLength": 300 },
  "TournamentUpdate.description": { "maxLength": 5000 },
  "TournamentUpdate.qualification_criteria": { "maxLength": 5000 },
  "TournamentUpdate.registration_instructions": { "maxLength": 5000 },
  "TournamentUpdate.eur_rate": { "exclusiveMinimum": 0 },
  "TournamentUpdate.reservation_validity_days": { "minimum": 2, "maximum": 7 },
  "TournamentUpdate.reminder_day": { "exclusiveMinimum": 0 },
  "TournamentUpdate.deposit_amount": { "minimum": 0 },
  "TournamentUpdate.deposit_amount_eur": { "minimum": 0 },
  "TournamentUpdate.amount_tolerance_percent": { "minimum": 0, "maximum": 100 },
  "TournamentUpdate.bank_account": { "maxLength": 50, "pattern": "^([A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}|[0-9]{1,6}-?[0-9]{2,10}/[0-9]{4})$" },
  "TournamentUpdate.expiry_grace_hours": { "minimum": 0 },
  "TournamentUpdate.fio_token": { "maxLength": 200 },
  "TournamentUpdate.output_sheet_url": { "maxLength": 500 },
  "TournamentUpdate.weapon_rental_fee": { "minimum": 0 },
  "TournamentUpdate.weapon_rental_fee_early": { "minimum": 0 },
  "TournamentUpdate.afterparty_fee": { "minimum": 0 },
  "TournamentUpdate.afterparty_fee_early": { "minimum": 0 },
  "TournamentUpdate.vs_series": { "minimum": 1, "maximum": 99 },
  "TournamentUpdate.hr_category_map_key": { "maxLength": 200 },
  "TournamentUpdate.hr_category_map_value": { "maxLength": 200 },
  "RuleIn.phase": { "maxLength": 20 },
  "RuleIn.kind": { "maxLength": 30 },
  "RuleIn.target": { "maxLength": 50 },
  "TeamEntryIn.name": { "minLength": 1, "maxLength": 200 },
  "RosterMemberIn.name": { "minLength": 1, "maxLength": 200 },
  "RosterMemberIn.club": { "maxLength": 200 },
  "RosterMemberIn.nationality": { "maxLength": 100 },
};

// A discipline's capacity ceiling depends on `kind` (an owner decision, not
// a tier): a team discipline's capacity counts teams, an individual's counts
// fencers. Resolved per row, never a static FIELD_CONSTRAINTS entry, the
// same way MONEY_MAX is resolved per currency.
export const DISCIPLINE_CAPACITY_MAX: Record<string, number> = {
  "individual": 200,
  "team": 64,
};

// An extra item's max_qty ceiling depends on `category`. Action categories
// (seminar/afterparty/other_action) are always forced to 1 by the backend
// regardless of what is submitted, so they carry no ceiling here.
export const EXTRA_ITEM_MAX_QTY_CEILING: Record<string, number> = {
  "rental": 10,
  "merch": 100,
  "other_item": 100,
};

// Every fee/price/discount-amount field is a non-negative whole unit of its
// currency, ceiling per currency (design D4). Resolved per request from the
// currency the field actually carries — never a static bound in
// FIELD_CONSTRAINTS above, since a local-currency field's ceiling depends on
// the tournament it belongs to.
export const MONEY_MAX: Record<string, number> = {
  "CZK": 10000,
  "EUR": 1000,
};

export const PERCENT_MAX = 100;
