from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from repocodex import ENGINE_VERSION

FRONTMATTER_DELIM = "---"
OKF_VERSION = "0.2"
PROCESS_RG = "process:repocodex-rg"


class ConceptType(str, Enum):
    TechnicalDecision = "TechnicalDecision"
    InvariantContract = "InvariantContract"
    BusinessWorkflow = "BusinessWorkflow"
    GuardrailDecision = "GuardrailDecision"


class ConceptStatus(str, Enum):
    draft = "draft"
    stable = "stable"
    deprecated = "deprecated"


class Claim(BaseModel):
    model_config = ConfigDict(extra="allow")
    literal: str
    subject: str | None = None
    anchor: int | None = None


class Anchor(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str
    all_of: list[str]
    near: str | None = None
    scope_lines: int | None = None
    min_match: int | None = None


class Verification(BaseModel):
    model_config = ConfigDict(extra="allow")
    engine: str = "ripgrep"
    anchors: list[Anchor] = Field(default_factory=list)


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")
    resource: str
    id: str | None = None
    title: str | None = None
    author: str | None = None
    usage_count: int | None = None
    last_modified: str | None = None


class ActorStamp(BaseModel):
    model_config = ConfigDict(extra="allow")
    by: str
    at: str | None = None

    @field_validator("by", mode="before")
    @classmethod
    def _normalize_actor(cls, value: Any) -> str:
        return normalize_actor(str(value))

    @field_validator("at", mode="before")
    @classmethod
    def _at_as_str(cls, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            iso = value.isoformat()
            if iso.endswith("+00:00"):
                return iso[:-6] + "Z"
            return iso
        return str(value)


def normalize_actor(value: str) -> str:
    if value.startswith("agent:"):
        return value[len("agent:") :]
    return value


def source_from_string(value: str) -> Source:
    if value.startswith("commit:"):
        sha = value[len("commit:") :]
        return Source(resource=f"git://commit/{sha}", title="commit", id=sha)
    return Source(resource=value)


def coerce_source(item: Any) -> Source:
    if isinstance(item, Source):
        return item
    if isinstance(item, str):
        return source_from_string(item)
    if isinstance(item, dict):
        return Source.model_validate(item)
    raise ValueError("sources entries must be objects with resource")


def coerce_sources(value: Any) -> list[Source] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("sources must be a list")
    return [coerce_source(item) for item in value]


def coerce_verified(value: Any) -> ActorStamp | list[ActorStamp] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [ActorStamp.model_validate(item) for item in value]
    if isinstance(value, ActorStamp):
        return value
    return ActorStamp.model_validate(value)


def type_str(value: Any) -> str:
    if hasattr(value, "value") and not isinstance(value, str):
        return str(value.value)
    return str(value)


class ConceptFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    generated: ActorStamp | dict[str, Any] | None = None
    verified: ActorStamp | list[ActorStamp] | dict[str, Any] | None = None
    status: ConceptStatus = ConceptStatus.stable
    stale_after: str | None = None
    sources: list[Source] | None = None
    verification: Verification | None = None
    claims: list[Claim] | None = None
    supersedes: str | None = None
    rationale: str | None = None
    contract_id: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _type_as_str(cls, value: Any) -> str:
        if value is None or value == "":
            raise ValueError("type is required")
        return type_str(value)

    @field_validator("generated", mode="before")
    @classmethod
    def _generated(cls, value: Any) -> ActorStamp | None:
        if value is None:
            return None
        if isinstance(value, ActorStamp):
            return value
        return ActorStamp.model_validate(value)

    @field_validator("verified", mode="before")
    @classmethod
    def _verified(cls, value: Any) -> ActorStamp | list[ActorStamp] | None:
        return coerce_verified(value)

    @field_validator("sources", mode="before")
    @classmethod
    def _sources(cls, value: Any) -> list[Source] | None:
        return coerce_sources(value)

    def extra_keys(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


class ConceptDocument(BaseModel):
    identity: str
    frontmatter: ConceptFrontmatter
    body: str

    @property
    def status(self) -> ConceptStatus:
        return self.frontmatter.status

    @property
    def anchors(self) -> list[Anchor]:
        if not self.frontmatter.verification:
            return []
        return self.frontmatter.verification.anchors

    @property
    def pinned_paths(self) -> list[str]:
        return [anchor.path for anchor in self.anchors]


class IndexDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    okf_version: str | None = None
    body: str = ""
    extras: dict[str, Any] = Field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp(by: str = PROCESS_RG) -> dict[str, str]:
    return {"by": normalize_actor(by), "at": utc_now()}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith(FRONTMATTER_DELIM):
        return {}, text
    rest = stripped[len(FRONTMATTER_DELIM) :]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find(f"\n{FRONTMATTER_DELIM}")
    if end < 0:
        data = yaml.safe_load(rest) or {}
        return (data if isinstance(data, dict) else {}), ""
    raw_yaml = rest[:end]
    body = rest[end + len(f"\n{FRONTMATTER_DELIM}") :]
    if body.startswith("\n"):
        body = body[1:]
    data = yaml.safe_load(raw_yaml) or {}
    if not isinstance(data, dict):
        data = {}
    return data, body


def parse_concept(text: str, identity: str) -> ConceptDocument:
    data, body = split_frontmatter(text)
    frontmatter = ConceptFrontmatter.model_validate(data)
    return ConceptDocument(identity=identity, frontmatter=frontmatter, body=body)


def parse_index(text: str) -> IndexDocument:
    data, body = split_frontmatter(text)
    extras = {k: v for k, v in data.items() if k not in {"okf_version", "format_version"}}
    version = data.get("okf_version")
    return IndexDocument(
        okf_version=str(version) if version is not None else None,
        body=body,
        extras=extras,
    )


def _dump_yaml(data: dict[str, Any]) -> str:
    dumped = yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    return dumped.rstrip() + "\n"


def _dump_source(source: Any) -> dict[str, Any]:
    item = coerce_source(source)
    return item.model_dump(mode="python", exclude_none=True)


def _dump_stamp(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return [_dump_stamp(item) for item in value]
    if isinstance(value, ActorStamp):
        data = value.model_dump(mode="python", exclude_none=True)
        if "by" in data:
            data["by"] = normalize_actor(str(data["by"]))
        return data
    if isinstance(value, dict):
        data = dict(value)
        if "by" in data:
            data["by"] = normalize_actor(str(data["by"]))
        return data
    return value


def _frontmatter_dict(frontmatter: ConceptFrontmatter) -> dict[str, Any]:
    data = frontmatter.model_dump(mode="python", exclude_none=True)
    for key, value in (frontmatter.model_extra or {}).items():
        data[key] = value
    data["type"] = type_str(data.get("type", frontmatter.type))
    if "status" in data and hasattr(data["status"], "value"):
        data["status"] = data["status"].value
    if data.get("sources") is not None:
        data["sources"] = [_dump_source(item) for item in data["sources"]]
    if "generated" in data:
        data["generated"] = _dump_stamp(data["generated"])
    if "verified" in data:
        data["verified"] = _dump_stamp(data["verified"])
    return data


def serialize_concept(doc: ConceptDocument) -> str:
    payload = _dump_yaml(_frontmatter_dict(doc.frontmatter))
    body = doc.body if doc.body.endswith("\n") or doc.body == "" else doc.body + "\n"
    return f"{FRONTMATTER_DELIM}\n{payload}{FRONTMATTER_DELIM}\n\n{body}"


def serialize_index(index: IndexDocument) -> str:
    data: dict[str, Any] = {}
    if index.okf_version is not None:
        data["okf_version"] = index.okf_version
    data.update(index.extras)
    if not data:
        return index.body
    payload = _dump_yaml(data)
    body = index.body if index.body.endswith("\n") or index.body == "" else index.body + "\n"
    return f"{FRONTMATTER_DELIM}\n{payload}{FRONTMATTER_DELIM}\n\n{body}"


def identity_from_path(context_root: str, path: str) -> str:
    rel = path.replace("\\", "/")
    prefix = context_root.rstrip("/") + "/"
    if rel.startswith(prefix):
        rel = rel[len(prefix) :]
    if rel.endswith(".md"):
        rel = rel[: -len(".md")]
    return rel


def envelope(payload: dict[str, Any], engine_version: str = ENGINE_VERSION) -> dict[str, Any]:
    return {**payload, "engine_version": engine_version}
