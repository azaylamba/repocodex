from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from repocodex import ENGINE_VERSION

FRONTMATTER_DELIM = "---"


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


class ActorStamp(BaseModel):
    model_config = ConfigDict(extra="allow")
    by: str
    at: str


class ConceptFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: ConceptType
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    generated: ActorStamp | dict[str, Any] | None = None
    verified: ActorStamp | dict[str, Any] | None = None
    status: ConceptStatus = ConceptStatus.draft
    stale_after: str | None = None
    sources: list[str] | None = None
    verification: Verification
    claims: list[Claim] | None = None
    supersedes: str | None = None
    rationale: str | None = None
    contract_id: str | None = None

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
        return self.frontmatter.verification.anchors

    @property
    def pinned_paths(self) -> list[str]:
        return [anchor.path for anchor in self.anchors]


class IndexDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    format_version: str | None = None
    body: str = ""
    extras: dict[str, Any] = Field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp(by: str = "process:repocodex-rg") -> dict[str, str]:
    return {"by": by, "at": utc_now()}


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
    extras = {k: v for k, v in data.items() if k != "format_version"}
    return IndexDocument(
        format_version=str(data["format_version"]) if "format_version" in data else None,
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


def _frontmatter_dict(frontmatter: ConceptFrontmatter) -> dict[str, Any]:
    data = frontmatter.model_dump(mode="python", exclude_none=True)
    for key, value in (frontmatter.model_extra or {}).items():
        data[key] = value
    if "type" in data and hasattr(data["type"], "value"):
        data["type"] = data["type"].value
    if "status" in data and hasattr(data["status"], "value"):
        data["status"] = data["status"].value
    return data


def serialize_concept(doc: ConceptDocument) -> str:
    payload = _dump_yaml(_frontmatter_dict(doc.frontmatter))
    body = doc.body if doc.body.endswith("\n") or doc.body == "" else doc.body + "\n"
    return f"{FRONTMATTER_DELIM}\n{payload}{FRONTMATTER_DELIM}\n\n{body}"


def serialize_index(index: IndexDocument) -> str:
    data: dict[str, Any] = {}
    if index.format_version is not None:
        data["format_version"] = index.format_version
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
