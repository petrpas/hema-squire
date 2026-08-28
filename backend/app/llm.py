"""The one place where Anthropic credentials become a pydantic-ai model.

The key alone does not authorise a request: an identity-linked API key is
scoped to a workspace, and the API rejects a call that does not name which one
it acts in. The workspace id therefore rides on every request as a default
header, which the plain `model="anthropic:..."` string form has no room for.
"""

from functools import lru_cache

from app.config import settings


def llm_configured() -> bool:
    return bool(settings.anthropic_api_key)


@lru_cache(maxsize=1)
def get_model():
    """The shared model for every LLM call site (parse, match, dedup)."""
    from anthropic import AsyncAnthropic
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider

    headers = {}
    if settings.anthropic_workspace_id:
        headers["anthropic-workspace-id"] = settings.anthropic_workspace_id
    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key, default_headers=headers or None
    )
    name = settings.llm_model.removeprefix("anthropic:")
    return AnthropicModel(name, provider=AnthropicProvider(anthropic_client=client))
