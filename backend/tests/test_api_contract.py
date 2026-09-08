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
from tests import contract_seed

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
def seeded(client, auth_headers, engine):
    """One tournament with something of everything, built once per operation.

    A fixture rather than a call in the test body: the body runs once per
    generated input, so a second signup would answer 409 and a second tournament
    409 again. The scope this belongs to is the test function, which is also the
    scope of the database it writes to."""
    return contract_seed.build(client, auth_headers, engine)


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
def test_api_contract(case, seeded):
    """Every operation, authenticated, against a tournament that exists.

    Both halves are deliberate. Unauthenticated, every guarded route answers 401
    from the dependency and no handler is reached. Unseeded, a generated `slug`
    answers 404 for the same reason — three quarters of all requests did, and
    only 15 of 108 operations ever reached a 2xx. Substituting the real ids
    leaves the bodies and queries fuzzed, which is where a generated value can
    find something a random id never will.
    """
    # The trade this makes: a path id is no longer fuzzed, so an id the route
    # cannot handle — 2**63 overflows SQLite's INTEGER, which is a 500 the body
    # fields were bounded against — is not reached through a path parameter.
    # Worth it: unsubstituted, three quarters of every request answered 404 and
    # the handlers behind them were never run at all.
    for name, value in seeded.path_params.items():
        if case.path_parameters and name in case.path_parameters:
            case.path_parameters[name] = value
    case.call_and_validate(headers=seeded.headers, checks=CONTRACT_CHECKS)
