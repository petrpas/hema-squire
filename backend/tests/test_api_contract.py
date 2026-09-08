"""Contract fuzzing over the OpenAPI schema FastAPI publishes (phase 4 of
`openspec/changes/static-analysis-spec.md`).

One file, every operation. Schemathesis reads the schema and generates the
inputs from it, so this asks something the hand-written suite does not: for
anything the schema says is a valid request, does the app answer without
falling over, and does what it answers match what the schema promised.
"""

import hypothesis
import pytest
import schemathesis
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import response_schema_conformance

from app.main import app

# Exactly the two questions this phase set out to ask (static-analysis spec,
# phase 4): does a schema-valid request ever produce a 500, and does what comes
# back match what the schema promised. Schemathesis v4 offers a dozen more, and
# the rest were tried and turned off deliberately:
#
#   status_code_conformance   FastAPI documents 200 and 422 and nothing else,
#                             so every 401/403/404/409 this application returns
#                             on purpose reads as undocumented. 188 findings,
#                             all of them the framework's default docs.
#   missing_required_header   Reports 404 where it wanted 401, because a route's
#                             tournament lookup resolves before its auth
#                             dependency. Real, and a deliberate non-secret: a
#                             slug is public in `/api/tournaments/open`, so the
#                             404 discloses nothing the listing does not.
#   unsupported_method,       Starlette answers 404 rather than 405 for an
#   allow_header_conformance  undeclared method, and its `Allow` header is its
#                             own. Framework behaviour, not this application's.
#   positive_data_acceptance  Generates strings for `format: email` that
#                             `email-validator` rejects. The rejection is right.
#   negative_data_rejection   Counts pydantic's documented coercion as a schema
#                             violation.
CONTRACT_CHECKS = [not_a_server_error, response_schema_conformance]

schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@pytest.fixture
def organizer_headers(auth_headers):
    """One account per operation, not per generated input.

    Signing up inside the test body would run once per example and the second
    would answer 409 `email_already_registered`. A fixture is resolved once for
    the test function, which is the scope the account belongs to."""
    return auth_headers()


@schema.parametrize()
@hypothesis.settings(
    # The database is built by the `client` fixture, which is function-scoped,
    # so it is not rebuilt between the inputs Hypothesis generates for one
    # operation — state accumulates across them. That is deliberate here rather
    # than merely tolerated: the question this file asks is whether an
    # operation can be made to fall over, and a request arriving against a
    # database earlier requests have already written to is the ordinary case,
    # not a contrived one. Isolation that matters is per-operation, and each
    # generated test gets its own fixture and its own empty database.
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
)
def test_api_contract(case, client, organizer_headers):
    """Every operation, against an organizer's own token.

    Authenticated deliberately. Unauthenticated, every guarded route answers
    401 from the dependency and no handler is reached, which would fuzz the
    auth layer 108 times and the application not at all.
    """
    case.call_and_validate(headers=organizer_headers, checks=CONTRACT_CHECKS)
