from __future__ import annotations

import dataclasses
import enum
import json
import typing

from pydantic import JsonValue

from dragonglass.agent import AgentEvent


class OllamaModelRecord(typing.TypedDict, total=False):
    name: str
    model: str


OllamaModelEntry = str | OllamaModelRecord


class OpenCodeProviderModel(typing.TypedDict, total=False):
    id: str
    name: str


OpenCodeProviderModelEntry = str | OpenCodeProviderModel


class OpenCodeProviderRecord(typing.TypedDict, total=False):
    id: str
    models: list[OpenCodeProviderModelEntry]


EncodableValue = (
    JsonValue | AgentEvent | list["EncodableValue"] | dict[str, "EncodableValue"]
)


def _coerce_ollama_model_entry(value: JsonValue) -> OllamaModelEntry | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    name = value.get("name")
    model = value.get("model")
    parsed: OllamaModelRecord = {}
    if isinstance(name, str):
        parsed["name"] = name
    if isinstance(model, str):
        parsed["model"] = model
    return parsed if parsed else None


def _coerce_opencode_provider(value: JsonValue) -> OpenCodeProviderRecord | None:
    if not isinstance(value, dict):
        return None
    provider_id = value.get("id")
    models = value.get("models")
    if not isinstance(provider_id, str) or not isinstance(models, list):
        return None
    parsed_models: list[OpenCodeProviderModelEntry] = []
    for model in models:
        if isinstance(model, str):
            parsed_models.append(model)
            continue
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        model_name = model.get("name")
        parsed_model: OpenCodeProviderModel = {}
        if isinstance(model_id, str):
            parsed_model["id"] = model_id
        if isinstance(model_name, str):
            parsed_model["name"] = model_name
        if parsed_model:
            parsed_models.append(parsed_model)
    return {"id": provider_id, "models": parsed_models}


class Command(enum.StrEnum):
    CHAT = "chat"
    STOP = "stop"
    APPROVE = "approve"
    REJECT = "reject"
    APPROVE_SESSION = "approve_session"
    PING = "ping"
    GET_CONFIG = "get_config"
    SET_CONFIG = "set_config"
    LIST_MODELS = "list_models"
    SAVE_MODEL = "save_model"
    GET_VERSION = "get_version"
    NEW_CHAT = "new_chat"
    LIST_CONVERSATIONS = "list_conversations"
    LOAD_CONVERSATION = "load_conversation"
    DELETE_CONVERSATION = "delete_conversation"
    OPEN_NOTE = "open_note"


def serialize_event(event: AgentEvent) -> str:
    def _encode(obj: EncodableValue) -> JsonValue:
        if dataclasses.is_dataclass(obj):
            result: dict[str, JsonValue] = {"type": obj.__class__.__name__}
            for field in dataclasses.fields(obj):
                value = getattr(obj, field.name)
                result[field.name] = _encode(value)
            return result
        if isinstance(obj, list):
            return [_encode(item) for item in obj]
        if isinstance(obj, dict):
            encoded: dict[str, JsonValue] = {}
            for key, value in obj.items():
                if isinstance(key, str):
                    encoded[key] = _encode(value)
            return encoded
        if obj is None or isinstance(obj, str | int | float | bool):
            return obj
        return str(obj)

    return json.dumps(_encode(event))


def resolve_chat_model(
    raw_model_override: str | None, selected_model: str
) -> str | None:
    if raw_model_override is not None:
        stripped = raw_model_override.strip()
        if stripped:
            return stripped
    selected = selected_model.strip()
    if selected:
        return selected
    return None


def is_embedding_model(model_name: str) -> bool:
    lowered = model_name.lower()
    return "embed" in lowered or "embedding" in lowered


def parse_ollama_models(raw_models: JsonValue) -> list[str]:
    if not isinstance(raw_models, list):
        return []

    parsed_models: list[str] = []
    for model in raw_models:
        entry = _coerce_ollama_model_entry(model)
        if entry is None:
            continue
        name: str | None = None
        if isinstance(entry, str):
            name = entry
        else:
            value = entry.get("name") or entry.get("model")
            if isinstance(value, str):
                name = value
        if not name:
            continue

        bare = name.strip()
        if bare.startswith("ollama_chat/"):
            bare = bare[len("ollama_chat/") :]
        elif bare.startswith("ollama/"):
            bare = bare[len("ollama/") :]
        display_name = f"ollama/{bare}"
        if not is_embedding_model(bare):
            parsed_models.append(display_name)

    return parsed_models


def parse_opencode_models(raw_providers: JsonValue) -> list[str]:
    if not isinstance(raw_providers, list):
        return []

    parsed_models: list[str] = []
    for provider in raw_providers:
        provider_entry = _coerce_opencode_provider(provider)
        if provider_entry is None:
            continue
        provider_id = provider_entry["id"]
        models = provider_entry["models"]
        for model in models:
            model_id = None
            if isinstance(model, str):
                model_id = model
            elif isinstance(model, dict):
                model_id = model.get("id") or model.get("name")
            if isinstance(model_id, str):
                parsed_models.append(f"{provider_id}/{model_id}")

    return parsed_models
