"""Models behind the assistant (app.yaml -> assistant.provider).

local: an open model behind an OpenAI-compatible chat server (Ollama, llama.cpp's llama-server).
anthropic: Claude through the Anthropic API (key in .env: ANTHROPIC_API_KEY).

Both run the same loop: ask, run the tools the model calls, send the results back, until the model
answers or max_tool_calls is reached; then one last round without tools.
"""
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from app.assistant.tools import ToolRun, json_schema
from app.core.config import settings
from app.core.config_files import AssistantConf, AssistantProviderConf

CallTool = Callable[[str, dict], Awaitable[ToolRun]]
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ProviderError(Exception):
    pass


@dataclass
class Reply:
    text: str
    refused: bool = False
    input_tokens: int = 0
    output_tokens: int = 0


class LocalProvider:
    """OpenAI-compatible /chat/completions with function tools."""

    name = "local"

    def __init__(self, conf: AssistantConf, p: AssistantProviderConf):
        self.conf, self.p, self.model = conf, p, p.model

    def _tools(self) -> list[dict]:
        return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                  "parameters": json_schema(t)}} for t in self.conf.tools]

    async def _post(self, client: httpx.AsyncClient, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {settings.assistant_local_api_key}"} if settings.assistant_local_api_key else {}
        try:
            r = await client.post(f"{self.p.base_url.rstrip('/')}/chat/completions", json=body, headers=headers)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e

    async def answer(self, system: str, messages: list[dict], call_tool: CallTool) -> Reply:
        msgs = [{"role": "system", "content": system}, *messages]
        reply, calls = Reply(""), 0
        async with httpx.AsyncClient(timeout=self.p.timeout_seconds) as client:
            while True:
                final = calls >= self.conf.max_tool_calls
                if final:
                    msgs.append({"role": "user", "content": self.conf.final_round_note})
                body = {"model": self.model, "messages": msgs, "max_tokens": self.p.max_tokens,
                        "tools": self._tools(), "tool_choice": "none" if final else "auto"}
                if self.p.temperature is not None:
                    body["temperature"] = self.p.temperature
                data = await self._post(client, body)
                usage = data.get("usage") or {}
                reply.input_tokens += usage.get("prompt_tokens") or 0
                reply.output_tokens += usage.get("completion_tokens") or 0
                msg = (data.get("choices") or [{}])[0].get("message") or {}
                tool_calls = msg.get("tool_calls") or []
                if not tool_calls or final:
                    reply.text = (msg.get("content") or "").strip()
                    return reply
                msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    if calls >= self.conf.max_tool_calls:
                        result = self.conf.final_round_note
                    else:
                        calls += 1
                        try:
                            args = json.loads(fn.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = None
                        result = ((await call_tool(fn.get("name", ""), args)).result if isinstance(args, dict)
                                  else "Los argumentos no son JSON válido.")
                    msgs.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})


class AnthropicProvider:
    """Claude Messages API with client tools (manual loop: the tools run inside this request)."""

    name = "anthropic"

    def __init__(self, conf: AssistantConf, p: AssistantProviderConf):
        self.conf, self.p, self.model = conf, p, p.model

    async def answer(self, system: str, messages: list[dict], call_tool: CallTool) -> Reply:
        import anthropic

        if not settings.anthropic_api_key:
            raise ProviderError("Falta ANTHROPIC_API_KEY en backend/.env")
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=self.p.timeout_seconds)
        tools = [{"name": t.name, "description": t.description, "input_schema": json_schema(t)} for t in self.conf.tools]
        msgs = list(messages)
        reply, calls, final = Reply(""), 0, False
        while True:
            kwargs = {"model": self.model, "max_tokens": self.p.max_tokens, "system": system, "tools": tools,
                      "messages": msgs, "cache_control": {"type": "ephemeral"},
                      "tool_choice": {"type": "none" if final else "auto"}}
            if self.p.effort:
                kwargs["output_config"] = {"effort": self.p.effort}
            if self.p.fallbacks:
                kwargs.update(betas=[FALLBACK_BETA], fallbacks=self.p.fallbacks)
            try:
                resp = await client.beta.messages.create(**kwargs)
            except anthropic.APIError as e:
                raise ProviderError(f"{type(e).__name__}: {e}") from e
            u = resp.usage
            reply.input_tokens += (u.input_tokens or 0) + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
            reply.output_tokens += u.output_tokens or 0
            if resp.stop_reason == "refusal":
                reply.refused = True
                return reply
            uses = [b for b in resp.content if b.type == "tool_use"]
            if not uses or final:
                reply.text = "".join(b.text for b in resp.content if b.type == "text").strip()
                return reply
            msgs.append({"role": "assistant", "content": resp.content})
            results = []
            for b in uses:
                if calls >= self.conf.max_tool_calls:
                    content, is_error = self.conf.final_round_note, True
                else:
                    calls += 1
                    run = await call_tool(b.name, b.input if isinstance(b.input, dict) else {})
                    content, is_error = run.result, not run.ok
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": is_error})
            final = calls >= self.conf.max_tool_calls
            if final:
                results.append({"type": "text", "text": self.conf.final_round_note})
            msgs.append({"role": "user", "content": results})


PROVIDERS = {"local": LocalProvider, "anthropic": AnthropicProvider}


def get_provider(conf: AssistantConf):
    if conf.provider not in PROVIDERS or conf.provider not in conf.providers:
        raise ProviderError(f"Proveedor desconocido: {conf.provider}")
    return PROVIDERS[conf.provider](conf, conf.providers[conf.provider])
