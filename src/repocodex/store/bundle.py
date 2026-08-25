from __future__ import annotations

from pathlib import Path

from repocodex.schema import (
    ConceptDocument,
    ConceptStatus,
    identity_from_path,
    parse_concept,
    parse_index,
    serialize_concept,
    serialize_index,
    split_frontmatter,
    stamp,
    utc_now,
)

RESERVED = {"index.md", "log.md", "reverse-index.md"}
SKIP_DIRS = {"repair-tasks"}


def discover_context_roots(repo: Path) -> list[Path]:
    roots: list[Path] = []
    for path in repo.rglob(".context"):
        if path.is_dir() and ".git" not in path.parts:
            roots.append(path)
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
            if "type" not in data or "verification" not in data:
                continue
            docs.append(parse_concept(text, identity))
    return docs


def concept_path(context_root: Path, identity: str) -> Path:
    return context_root / f"{identity}.md"


def ensure_bundle(context_root: Path, format_version: str = "1.0") -> None:
    context_root.mkdir(parents=True, exist_ok=True)
    index_path = context_root / "index.md"
    if not index_path.exists():
        index_path.write_text(
            f"---\nformat_version: \"{format_version}\"\n---\n\n# Context catalog\n",
            encoding="utf-8",
        )
    log_path = context_root / "log.md"
    if not log_path.exists():
        log_path.write_text("# log\n", encoding="utf-8")
    reverse = context_root / "reverse-index.md"
    if not reverse.exists():
        reverse.write_text("# reverse-index\n", encoding="utf-8")


def append_log(context_root: Path, message: str) -> None:
    log_path = context_root / "log.md"
    if not log_path.exists():
        log_path.write_text("# log\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {utc_now()} {message}\n")


def update_catalog(context_root: Path, doc: ConceptDocument) -> None:
    directory = (context_root / doc.identity).parent
    directory.mkdir(parents=True, exist_ok=True)
    index_path = directory / "index.md"
    title = doc.frontmatter.title or doc.identity
    link = f"- [{title}](./{Path(doc.identity).name}.md)"
    if index_path.exists():
        current = index_path.read_text(encoding="utf-8")
        if Path(doc.identity).name in current:
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
    verified_by: str = "process:repocodex-rg",
) -> Path:
    root = context_root or owning_context_root(repo, doc.pinned_paths)
    ensure_bundle(root)
    if doc.frontmatter.status == ConceptStatus.stable and not doc.frontmatter.verified:
        doc.frontmatter.verified = stamp(verified_by)
    path = concept_path(root, doc.identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_concept(doc), encoding="utf-8")
    update_catalog(root, doc)
    append_log(root, f"wrote {doc.identity} ({doc.frontmatter.type.value})")
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


def format_version(repo: Path) -> str | None:
    root = repo / ".context" / "index.md"
    if not root.exists():
        return None
    return parse_index(root.read_text(encoding="utf-8")).format_version
