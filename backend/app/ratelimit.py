"""Throttling for the endpoints that verify passwords.

Password verification is deliberately expensive (~100 ms of scrypt), which makes
an unthrottled login endpoint simultaneously the cheapest CPU-exhaustion target
in the system and a credential-stuffing surface.

The bucket key is the client address as the ASGI server reports it. In production
uvicorn runs with --proxy-headers behind a Caddy that overwrites X-Forwarded-For
with the connecting peer, so request.client is the real caller: without that,
every request would carry Caddy's container address, the limit would be one
global bucket, and a single scanner would lock out an entire tournament. Nothing
here reads a client-supplied header directly — the proxy establishes the address.

The throttle lives in the app rather than the proxy so Caddy stays a stock
binary instead of an xcaddy build maintained for one plugin.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Disabled only where many requests legitimately come from one address in one
# minute — the test suite. Production and dev leave it on.
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
