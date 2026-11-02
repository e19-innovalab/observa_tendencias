"""Tools the model may call: the read-only API endpoints listed in app.yaml -> assistant.tools.

They run in-process through the FastAPI app (same validation and answers the frontend gets), and
results are trimmed before the model reads them.
"""
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

from app.core.config_files import AssistantConf, AssistantTool, app_config

PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclass
class ToolRun:
    tool: str
    args: dict
    ok: bool
    result: str  # what the model reads (trimmed JSON or an error)
    data: object = None  # full JSON, for the numbers check
    link: str | None = None
    extra: dict = field(default_factory=dict)


def json_schema(tool: AssistantTool) -> dict:
    props, required = {}, []
    for name, p in tool.params.items():
        prop = {"type": p.type, "description": p.description}
        if p.enum:
            prop["enum"] = p.enum
        props[name] = prop
        if p.required:
            required.append(name)
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def _clean_args(tool: AssistantTool, args: dict) -> dict:
    """Only declared params, without empty values; ISO3 codes in upper case."""
    out = {}
    for k, v in (args or {}).items():
        if k not in tool.params or v in (None, ""):
            continue
        out[k] = v.strip().upper() if k == "country" and isinstance(v, str) else v
    return out


def _link(tool: AssistantTool, args: dict) -> str | None:
    if not tool.link:
        return None
    try:
        path = tool.link.path.format(**args)
    except KeyError:
        return None
    query = {k: args[k] for k in tool.link.query if args.get(k) not in (None, "")}
    return f"{path}?{urlencode(query)}" if query else path


def _trim(data, drop: set[str], max_items: int):
    if isinstance(data, dict):
        return {k: _trim(v, drop, max_items) for k, v in data.items() if k not in drop}
    if isinstance(data, list):
        return [_trim(v, drop, max_items) for v in data[:max_items]]
    return data


def provided_codes(tool: AssistantTool, data) -> set[str]:
    """Values of tool.provides in the results (a list of items or a single one)."""
    if not tool.provides:
        return set()
    items = data if isinstance(data, list) else [data]
    return {str(i[tool.provides]) for i in items if isinstance(i, dict) and i.get(tool.provides)}


def trimmed_text(data, conf: AssistantConf) -> str:
    text = json.dumps(_trim(data, set(conf.tool_result_drop_keys), conf.tool_result_max_items),
                      ensure_ascii=False, separators=(",", ":"))
    limit = conf.tool_result_max_chars
    return text if len(text) <= limit else text[:limit] + "…[recortado]"


async def run_tool(client: httpx.AsyncClient, conf: AssistantConf, api_prefix: str, name: str,
                   raw_args: dict, known: set[str]) -> ToolRun:
    """Runs one tool. known: codes already seen in the conversation; params with must_be_known
    only accept those, and codes the tool provides are added to it."""
    tool = next((t for t in conf.tools if t.name == name), None)
    if tool is None:
        return ToolRun(name, raw_args or {}, False, f"Herramienta desconocida: {name}")
    args = _clean_args(tool, raw_args)
    missing = [p for p in PLACEHOLDER.findall(tool.path) if p not in args]
    missing += [k for k, p in tool.params.items() if p.required and k not in args and k not in missing]
    if missing:
        return ToolRun(name, args, False, f"Faltan parámetros: {', '.join(missing)}")
    for k, p in tool.params.items():
        if p.must_be_known and k in args and str(args[k]) not in known:
            return ToolRun(name, args, False, app_config().assistant.messages["unknown_code"].format(value=args[k]))
    path = tool.path.format(**{k: str(v) for k, v in args.items()})
    query = {**tool.fixed, **{k: v for k, v in args.items() if f"{{{k}}}" not in tool.path}}
    try:
        r = await client.get(api_prefix + path, params=query)
    except httpx.HTTPError as e:
        return ToolRun(name, args, False, f"Error al consultar: {e}")
    if r.status_code != 200:
        detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text
        return ToolRun(name, args, False, f"Error {r.status_code}: {detail}")
    data = r.json()
    known |= provided_codes(tool, data)
    return ToolRun(name, args, True, trimmed_text(data, conf), data, _link(tool, args))
