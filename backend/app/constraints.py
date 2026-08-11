"""Single authoritative source for every editable field's declared bounds.

Every `Field(...)` bound in `app/schemas.py` is read from a constant defined
here, so a bound exists in exactly one place on the backend.
`frontend/src/constraints.ts` is a hand-maintained, flat, literal-only mirror
of the same figures; `backend/tests/test_constraints_mirror.py` builds the
app's OpenAPI schema and checks the mirror against what the backend actually
publishes, so drift between the two fails the suite rather than reaching a
user.

Bounds here are *transcribed*, not invented, wherever one already existed
before this module — see design `add-field-validation` D1 and D4.
"""

# ---- string length tiers (design D4) ----
SHORT = 200
TEXT_MIN = 300
TEXT_MAX = 500
MARKDOWN = 5000

# ---- money (design D4): a non-negative whole unit, ceiling per currency ----
MONEY_MAX = {
    "CZK": 10_000,
    "EUR": 1_000,
}
PERCENT_MAX = 100

# ---- patterns ----
TOURNAMENT_SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,98}$"
# design D6: the alphabet a normalized discipline slug can ever contain: a
# kind-prefixed slug reaches 18 characters at "Team-Plastic-LSW-2", so 30 (the
# column width) rather than a shorter figure. Applied only after normalization
# runs (app/fieldtypes.py) — see 8a.1.
DISCIPLINE_SLUG_PATTERN = r"^[A-Za-z0-9-]{1,30}$"
DISCIPLINE_SLUG_MAX_LENGTH = 30
# a loose shape only: an IBAN, or the Czech domestic form
# [prefix-]number/bankcode — checksum validation (accounts.parse) is what
# actually decides validity (design accept-czech-account-format D5)
BANK_ACCOUNT_PATTERN = r"^([A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}|[0-9]{1,6}-?[0-9]{2,10}/[0-9]{4})$"

# ---- SignupIn / AccountUpdate ----
PASSWORD_MIN_LENGTH = 8
DISPLAY_NAME_MIN_LENGTH = 1
DISPLAY_NAME_MAX_LENGTH = SHORT
CLUB_MAX_LENGTH = SHORT
NATIONALITY_MAX_LENGTH = 100

# ---- PleaIn ----
PLEA_MESSAGE_MAX_LENGTH = 1000

# ---- DisciplineIn (weapon/slug lengths transcribed from
# discipline-identity-modal; the slug pattern is this change's own D6) ----
DISCIPLINE_WEAPON_MIN_LENGTH = 1
DISCIPLINE_WEAPON_MAX_LENGTH = 30
DISCIPLINE_NAME_MAX_LENGTH = 100  # matches the String(100) column
DISCIPLINE_SCHEDULE_WHEN_MAX_LENGTH = SHORT
DISCIPLINE_SCHEDULE_WHERE_MAX_LENGTH = 300
DISCIPLINE_RULESET_NAME_MAX_LENGTH = 100
DISCIPLINE_RULESET_URL_MAX_LENGTH = 500
TEAM_BOUND_MIN = 1
# capacity's ceiling depends on kind (an owner decision, not a tier): a team
# discipline's capacity counts teams, an individual's counts fencers, so the
# two have no reason to share one figure. Enforced by a model_validator
# (schemas.py), not a static Field bound, since it depends on another field.
DISCIPLINE_CAPACITY_MAX = {
    "individual": 200,
    "team": 64,
}

# ---- ExtraItemIn ----
EXTRA_ITEM_NAME_MIN_LENGTH = 1
EXTRA_ITEM_NAME_MAX_LENGTH = SHORT
EXTRA_ITEM_MAX_QTY_MIN = 1
EXTRA_ITEM_SCHEDULE_WHEN_MAX_LENGTH = SHORT
EXTRA_ITEM_SCHEDULE_WHERE_MAX_LENGTH = 300
EXTRA_ITEM_REMARK_MAX_LENGTH = 500
EXTRA_ITEM_OPTION_LABEL_MAX_LENGTH = 50
# max_qty's ceiling depends on category (an owner decision): a rental is
# physical and scarce, merch and other items are not. Action categories
# (seminar/afterparty/other_action) are always forced to 1 by the router and
# carry no ceiling of their own. Enforced by a model_validator, not a static
# Field bound, since it depends on another field.
EXTRA_ITEM_MAX_QTY_CEILING = {
    "rental": 10,
    "merch": 100,
    "other_item": 100,
}
# an option answer is a size, a shirt cut, a meal choice — never prose
OPTION_VALUE_MAX_LENGTH = 100

# ---- DiscountCondition / DiscountEffect / DiscountIn ----
DISCOUNT_COUNT_MIN = 1
DISCOUNT_NAME_MIN_LENGTH = 1
DISCOUNT_NAME_MAX_LENGTH = SHORT

# ---- OrganizerIn ----
ORGANIZER_NAME_MIN_LENGTH = 1
ORGANIZER_NAME_MAX_LENGTH = SHORT
ORGANIZER_LINK_MAX_LENGTH = 500

# ---- TournamentCreate / TournamentUpdate ----
TOURNAMENT_DISPLAY_NAME_MIN_LENGTH = 1
TOURNAMENT_DISPLAY_NAME_MAX_LENGTH = SHORT
TOURNAMENT_SUBTITLE_MAX_LENGTH = 400
TOURNAMENT_LOCATION_MAX_LENGTH = 300
TOURNAMENT_DESCRIPTION_MAX_LENGTH = MARKDOWN
TOURNAMENT_QUALIFICATION_CRITERIA_MAX_LENGTH = MARKDOWN
TOURNAMENT_REGISTRATION_INSTRUCTIONS_MAX_LENGTH = MARKDOWN
TOURNAMENT_BANK_ACCOUNT_MAX_LENGTH = 50  # matches the String(50) column
TOURNAMENT_FIO_TOKEN_MAX_LENGTH = SHORT
TOURNAMENT_OUTPUT_SHEET_URL_MAX_LENGTH = 500
HR_CATEGORY_MAP_KEY_MAX_LENGTH = SHORT
HR_CATEGORY_MAP_VALUE_MAX_LENGTH = SHORT
VS_SERIES_MIN = 1
VS_SERIES_MAX = 99
# the payment window: the interval between money being requested and money
# being due. Its floor is a bank transfer's settlement time, its ceiling is
# how long a tournament can afford to hold a seat on trust. Enforced on write
# only (design add-payment-modes Decision 9) — the shipped default was 10 and
# live tournaments carry it, so stored values are left alone and validated on
# the next edit rather than clamped to satisfy a UI range.
RESERVATION_VALIDITY_DAYS_MIN = 2
RESERVATION_VALIDITY_DAYS_MAX = 7

# ---- RuleIn ----
RULE_PHASE_MAX_LENGTH = 20
RULE_KIND_MAX_LENGTH = 30
RULE_TARGET_MAX_LENGTH = 50

# ---- TeamEntryIn / RosterMemberIn ----
TEAM_NAME_MIN_LENGTH = 1
TEAM_NAME_MAX_LENGTH = SHORT
ROSTER_MEMBER_NAME_MIN_LENGTH = 1
ROSTER_MEMBER_NAME_MAX_LENGTH = SHORT
ROSTER_MEMBER_CLUB_MAX_LENGTH = SHORT
ROSTER_MEMBER_NATIONALITY_MAX_LENGTH = 100

# ---- ExtraSelectionIn ----
EXTRA_SELECTION_QTY_MIN = 1

# ---- LinkIn ----
LINK_VS_MIN_ITEMS = 1
