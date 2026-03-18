from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def fail(message: str) -> None:
    raise SystemExit(message)


def parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_PATTERN.fullmatch(version)
    if not match:
        fail(f"Unsupported version '{version}'. Expected MAJOR.MINOR.PATCH.")
    return tuple(int(part) for part in match.groups())


def format_semver(parts: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in parts)


def bump_version(current: str, release_type: str) -> str:
    major, minor, patch = parse_semver(current)
    if release_type == "patch":
        return format_semver((major, minor, patch + 1))
    if release_type == "minor":
        return format_semver((major, minor + 1, 0))
    if release_type == "major":
        return format_semver((major + 1, 0, 0))
    fail(f"Unsupported bump type '{release_type}'. Use patch, minor, major, or set.")


def replace_pyproject_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, replacements = re.subn(
        r'(?m)^version = "[^"]+"$',
        f'version = "{version}"',
        content,
        count=1,
    )
    if replacements != 1:
        fail(f"Could not update version in {path}.")
    path.write_text(updated, encoding="utf-8")


def update_release_manifest(path: Path, version: str) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["release"] = version
    manifest["frontend"] = version
    manifest["backend"] = version
    manifest["worker"] = version
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def update_package_json(path: Path, version: str) -> None:
    package = json.loads(path.read_text(encoding="utf-8"))
    package["version"] = version
    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def update_package_lock(path: Path, version: str) -> None:
    lock = json.loads(path.read_text(encoding="utf-8"))
    lock["version"] = version
    root_package = lock.get("packages", {}).get("")
    if isinstance(root_package, dict):
        root_package["version"] = version
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        fail(
            "Usage: python scripts/bump_release.py <patch|minor|major>\n"
            "   or: python scripts/bump_release.py set <MAJOR.MINOR.PATCH>"
        )

    repo_root = Path(__file__).resolve().parents[1]
    release_manifest_path = repo_root / "release.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    current_version = release_manifest["release"]

    command = argv[1]
    if command == "set":
        if len(argv) != 3:
            fail("The set command requires an explicit version.")
        next_version = argv[2]
        parse_semver(next_version)
    else:
        if len(argv) != 2:
            fail(f"The {command} command does not accept an explicit version.")
        next_version = bump_version(current_version, command)

    update_release_manifest(release_manifest_path, next_version)
    update_package_json(repo_root / "frontend" / "package.json", next_version)
    update_package_lock(repo_root / "frontend" / "package-lock.json", next_version)
    replace_pyproject_version(repo_root / "backend" / "pyproject.toml", next_version)
    replace_pyproject_version(repo_root / "worker" / "pyproject.toml", next_version)

    print(f"Updated release version: {current_version} -> {next_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
