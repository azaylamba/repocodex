from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from repocodex.config import SKIP_WALK_DIR_NAMES
from repocodex.schema import (
    ConceptDocument,
    ConceptStatus,
    OKF_VERSION,
    identity_from_path,
    parse_concept,
    parse_index,
    serialize_concept,
    split_frontmatter,
    type_str,
)

RESERVED = {"index.md", "log.md"}
SKIP_DIRS = {"repair-tasks"}


def discover_context_roots(repo: Path) -> list[Path]:
    roots: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(repo, topdown=True, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in SKIP_WALK_DIR_NAMES]
        current = Path(dirpath)
        if current.name == ".context":
            roots.append(current)
            dirnames.clear()
    roots.sort(key=lambda p: (len(p.parts), str(p)))
    return roots


def owning_context_root(repo: Path, pinned_paths: list[str]) -> Path:
    repo = repo.resolve()
    roots = discover_context_roots(repo)
    root_bundle = repo / ".context"
    if not pinned_paths:
        return root_bundle if root_bundle.exists() else (roots[0] if roots else root_bundle)
    matching: list[Path] = []
    for ctx in roots:
        if ctx.resolve() == root_bundle.resolve():
            continue
        owner = ctx.parent
        try:
            prefix = str(owner.relative_to(repo)).replace("\\", "/").rstrip("/") + "/"
        except ValueError:
            continue
        if all(path.replace("\\", "/").startswith(prefix) for path in pinned_paths):
            matching.append(ctx)
    if not matching:
        return root_bundle if root_bundle.exists() or not roots else roots[0]
    matching.sort(key=lambda p: len(p.parts), reverse=True)
    return matching[0]


def concept_files(context_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(context_root.rglob("*.md")):
        if path.name in RESERVED:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def load_concepts(repo: Path) -> list[ConceptDocument]:
    docs: list[ConceptDocument] = []
    for context_root in discover_context_roots(repo):
        for path in concept_files(context_root):
            identity = identity_from_path(str(context_root), str(path))
            text = path.read_text(encoding="utf-8")
            data, _body = split_frontmatter(text)
            if "type" not in data or not data["type"]:
                continue
            docs.append(parse_concept(text, identity))
    return docs


def concept_path(context_root: Path, identity: str) -> Path:
    return context_root / f"{identity}.md"


def ensure_bundle(context_root: Path, okf_version: str = OKF_VERSION) -> None:
    context_root.mkdir(parents=True, exist_ok=True)
    index_path = context_root / "index.md"
    if not index_path.exists():
        index_path.write_text(
            f'---\nokf_version: "{okf_version}"\n---\n\n# Context catalog\n',
            encoding="utf-8",
        )
    log_path = context_root / "log.md"
    if not log_path.exists():
        log_path.write_text("# log\n", encoding="utf-8")


def append_log(context_root: Path, message: str) -> None:
    log_path = context_root / "log.md"
    today = datetime.now(timezone.utc).date().isoformat()
    heading = f"## {today}"
    parts = message.split(" ", 1)
    if len(parts) == 2:
        entry = f"- **{parts[0]}** {parts[1]}"
    else:
        entry = f"- **{message}**"
    if not log_path.exists():
        log_path.write_text(f"# log\n\n{heading}\n\n{entry}\n", encoding="utf-8")
        return
    text = log_path.read_text(encoding="utf-8")
    if heading in text:
        lines = text.splitlines(keepends=True)
        out: list[str] = []
        inserted = False
        i = 0
        while i < len(lines):
            line = lines[i]
            out.append(line)
            if not inserted and line.strip() == heading:
                i += 1
                if i < len(lines) and lines[i].strip() == "":
                    out.append(lines[i])
                    i += 1
                out.append(entry + "\n")
                out.extend(lines[i:])
                inserted = True
                break
            i += 1
        if not inserted:
            out.append(f"\n{heading}\n\n{entry}\n")
        log_path.write_text("".join(out), encoding="utf-8")
        return
    stripped = text.rstrip() + "\n"
    block = f"{heading}\n\n{entry}\n\n"
    lines = stripped.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#"):
        insert_at = 1
        if insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
    prefix = "".join(lines[:insert_at])
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    log_path.write_text(prefix + block + "".join(lines[insert_at:]).lstrip("\n"), encoding="utf-8")


def _catalog_link(doc: ConceptDocument) -> str:
    title = doc.frontmatter.title or doc.identity
    name = Path(doc.identity).name
    link = f"- [{title}](./{name}.md)"
    if doc.frontmatter.description:
        link += f" — {doc.frontmatter.description}"
    return link


def update_catalog(context_root: Path, doc: ConceptDocument) -> None:
    directory = (context_root / doc.identity).parent
    directory.mkdir(parents=True, exist_ok=True)
    index_path = directory / "index.md"
    link = _catalog_link(doc)
    leaf = Path(doc.identity).name
    if index_path.exists():
        current = index_path.read_text(encoding="utf-8")
        if leaf in current:
            return
        index_path.write_text(current.rstrip() + f"\n{link}\n", encoding="utf-8")
        return
    heading = f"# {directory.name}\n\n{link}\n"
    index_path.write_text(heading, encoding="utf-8")
    root_index = context_root / "index.md"
    if root_index.exists():
        rel = str(directory.relative_to(context_root))
        marker = f"{rel}/index.md"
        text = root_index.read_text(encoding="utf-8")
        if marker not in text:
            root_index.write_text(
                text.rstrip() + f"\n- [{rel}](./{rel}/index.md)\n",
                encoding="utf-8",
            )


def write_concept(
    repo: Path,
    doc: ConceptDocument,
    *,
    context_root: Path | None = None,
    verified_by: str | None = None,
) -> Path:
    del verified_by
    root = context_root or owning_context_root(repo, doc.pinned_paths)
    ensure_bundle(root)
    path = concept_path(root, doc.identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_concept(doc), encoding="utf-8")
    update_catalog(root, doc)
    append_log(root, f"wrote {doc.identity} ({type_str(doc.frontmatter.type)})")
    return path


def deprecate_concept(repo: Path, identity: str, *, reason: str) -> None:
    for context_root in discover_context_roots(repo):
        path = concept_path(context_root, identity)
        if not path.exists():
            continue
        doc = parse_concept(path.read_text(encoding="utf-8"), identity)
        doc.frontmatter.status = ConceptStatus.deprecated
        path.write_text(serialize_concept(doc), encoding="utf-8")
        append_log(context_root, f"deprecated {identity}: {reason}")


def okf_version(repo: Path) -> str | None:
    root = repo / ".context" / "index.md"
    if not root.exists():
        return None
    return parse_index(root.read_text(encoding="utf-8")).okf_version


def format_version(repo: Path) -> str | None:
    """Deprecated alias; OKF v0.2 uses okf_version."""
    return okf_version(repo)


def okf_bundle_errors(repo: Path) -> list[dict]:
    errors: list[dict] = []
    for context_root in discover_context_roots(repo):
        shard = str(context_root.relative_to(repo))
        for path in sorted(context_root.rglob("*.md")):
            rel = str(path.relative_to(repo)).replace("\\", "/")
            if path.name == "reverse-index.md":
                errors.append({"shard": shard, "path": rel, "reason": "illegal_extra_file"})
                continue
            if path.name in RESERVED:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            data, _body = split_frontmatter(text)
            if "type" not in data or not str(data.get("type") or "").strip():
                errors.append({"shard": shard, "path": rel, "reason": "missing_type"})
    return errors
