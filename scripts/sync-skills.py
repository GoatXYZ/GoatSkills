import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
IGNORED = {
    ".git",
    ".DS_Store",
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return "~/" + str(path.relative_to(HOME))


def files(folder):
    for current, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in dirs:
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f"Nested symlink requires review: {path}")
        for name in sorted(names):
            path = Path(current) / name
            if name in IGNORED or path.suffix in {".pyc", ".pyo"}:
                continue
            if (
                name == ".env"
                or name.startswith(".env.")
                and name != ".env.example"
                or name == "secrets.edn"
                or path.suffix in {".key", ".pem"}
            ):
                raise ValueError(f"Credential-shaped file requires review: {path}")
            if path.is_symlink():
                raise ValueError(f"Nested symlink requires review: {path}")
            yield path


def personal_sources():
    seen = set()
    sources = []
    for location in [
        ".agents/skills",
        ".claude/skills",
        ".codex/skills",
        ".cursor/skills",
        ".config/opencode/skills",
    ]:
        for folder in sorted((HOME / location).glob("*")):
            if not (folder / "SKILL.md").is_file() or folder.resolve() in seen:
                continue
            seen.add(folder.resolve())
            destination = folder.name
            if any(entry[0] == destination for entry in sources):
                destination = (
                    "variants/" + location.split("/")[0].lstrip(".") + "/" + folder.name
                )
            sources.append((destination, folder.resolve()))
    for project in sorted((HOME / "Github").iterdir()):
        if not project.is_dir():
            continue
        for location in [
            ".agents/skills",
            ".claude/skills",
            ".github/skills",
            ".codex/skills",
            ".cursor/skills",
        ]:
            for folder in sorted((project / location).glob("*")):
                if (folder / "SKILL.md").is_file() and folder.resolve() not in seen:
                    seen.add(folder.resolve())
                    destination = (
                        "projects/"
                        + project.name
                        + "/"
                        + location.split("/")[0].lstrip(".")
                        + "/"
                        + folder.name
                    )
                    sources.append((destination, folder.resolve()))
    return sources


def provider_inventory():
    groups = [("OpenAI", "codex-system", None, HOME / ".codex/skills/.system")]
    cache = HOME / ".codex/plugins/cache"
    for registry in sorted(cache.glob("*")):
        for package in sorted(registry.glob("*")):
            versions = [p for p in package.glob("*") if p.is_dir()]
            if versions:
                latest = max(
                    versions,
                    key=lambda p: tuple(
                        int(n) for n in re.findall(r"\d+", p.name.split("-")[0])
                    ),
                )
                groups.append(
                    ("OpenAI", registry.name + "/" + package.name, latest.name, latest)
                )
    claude = HOME / ".claude/plugins/cache"
    for registry in sorted(claude.glob("*")):
        for package in sorted(registry.glob("*")):
            versions = [p for p in package.glob("*") if p.is_dir()]
            if versions:
                latest = max(
                    versions,
                    key=lambda p: tuple(
                        int(n) for n in re.findall(r"\d+", p.name.split("-")[0])
                    ),
                )
                groups.append(
                    ("Claude", registry.name + "/" + package.name, latest.name, latest)
                )
    groups.extend(
        [
            ("Claude", "synced", None, HOME / ".claude/skills/synced"),
            ("Cursor", "skills-cursor", None, HOME / ".cursor/skills-cursor"),
        ]
    )
    entries = []
    for provider, package, version, folder in groups:
        for path in sorted(folder.rglob("SKILL.md")):
            entries.append(
                {
                    "provider": provider,
                    "package": package,
                    "version": version,
                    "name": path.parent.name,
                    "path": str(path.relative_to(folder)),
                    "sha256": digest(path),
                }
            )
    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Back up installed personal and project skills, and inventory provider definitions."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Refresh the backup; otherwise check without changes.",
    )
    args = parser.parse_args()
    manifest = ROOT / "inventory/personal-skills.json"
    old = json.loads(manifest.read_text())
    stamp = str(date.today()) if args.write else old["snapshot_date"]
    sources = personal_sources()
    skills = []
    expected = {}
    for destination, folder in sources:
        records = []
        for path in files(folder):
            rel = str(path.relative_to(folder))
            record = {
                "path": rel,
                "sha256": digest(path),
                "executable": bool(path.stat().st_mode & 0o111),
            }
            records.append(record)
            expected[destination + "/" + rel] = (path, record)
        skills.append(
            {
                "name": folder.name,
                "destination": destination,
                "source": relative(folder),
                "files": records,
            }
        )
    previous = {
        s.get("destination", s["name"]) + "/" + f["path"]
        for s in old["skills"]
        for f in s["files"]
    }
    problems = []
    for rel, (source, record) in expected.items():
        target = ROOT / rel
        if ROOT not in target.resolve().parents:
            raise ValueError(f"Destination escapes repository: {rel}")
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if (
            not target.is_file()
            or digest(target) != record["sha256"]
            or bool(target.stat().st_mode & 0o111) != record["executable"]
        ):
            problems.append(rel)
    for rel in sorted(previous - expected.keys()):
        target = ROOT / rel
        if ROOT not in target.resolve().parents:
            raise ValueError(f"Stale destination escapes repository: {rel}")
        if args.write:
            target.unlink(missing_ok=True)
        elif target.exists():
            problems.append("stale: " + rel)
    personal = {
        "snapshot_date": stamp,
        "sources": [
            "~/.agents/skills",
            "~/.claude/skills",
            "~/.codex/skills",
            "~/.cursor/skills",
            "~/.config/opencode/skills",
            "~/Github/*/{.agents,.claude,.github,.codex,.cursor}/skills",
        ],
        "skills": skills,
    }
    provider = {
        "snapshot_date": stamp,
        "scope": "Latest cached plugin versions, Codex system skills, Claude synced skills and Cursor built-ins. Presence does not prove availability. Provider content is not copied.",
        "skills": provider_inventory(),
    }
    for path, value in [
        (manifest, personal),
        (ROOT / "inventory/provider-skills.json", provider),
    ]:
        if args.write:
            path.write_text(json.dumps(value, indent=2) + "\n")
        elif json.loads(path.read_text()) != value:
            problems.append(str(path.relative_to(ROOT)))
    if problems:
        raise SystemExit("Backup differs: " + ", ".join(problems[:25]))
    print(
        f"{'Updated' if args.write else 'Verified'} {len(skills)} personal/project skills, {len(expected)} files, {len(provider['skills'])} provider definitions."
    )


if __name__ == "__main__":
    main()
