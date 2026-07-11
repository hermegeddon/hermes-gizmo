# Anthropic Tool Search

When `gizmo.mode` is `anthropic_tool_search` and the provider/model appears Anthropic-family, the helper can add a Tool Search tool and mark non-hot tools with `defer_loading: true`.

The helper keeps configured `never_defer` tools hot and ensures at least one non-deferred tool remains, because all-deferred requests are invalid. Non-Anthropic providers receive the normal selected schema list.

Provider beta headers and final serialization must be handled by Hermes core because the plugin should not monkeypatch provider clients.


## Capability gating

Native Anthropic provider paths are treated as Tool Search capable. Bedrock, Vertex, and Azure Anthropic routes require an explicit capability signal, for example `gizmo.anthropic.tool_search_supported: true`, because a Claude model name alone does not prove that Hermes can serialize Tool Search headers for that provider path. OpenRouter/OpenAI/local providers fall back to keyword selection or eager mode and do not receive Anthropic-only Tool Search definitions.
