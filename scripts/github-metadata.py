#!/usr/bin/env python3
"""Check or apply the canonical getcolors GitHub descriptions and homepages."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ORG = "getcolors"
WORKSPACE_REPO = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = WORKSPACE_REPO.parent
MANIFEST = WORKSPACE_REPO / "repositories.json"
PRODUCTION_HOMEPAGES = {
    "colors-website": "https://www.getcolors.ai",
    "once-colors": "https://www.getcolors.ai",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write differences with gh repo edit")
    args = parser.parse_args()

    wanted = json.loads(MANIFEST.read_text())
    expected_checkouts = {name for name, data in wanted.items() if data.get("checkout", True)}
    actual_checkouts = {path.name for path in WORKSPACE_ROOT.iterdir() if (path / ".git").is_dir()}
    if expected_checkouts != actual_checkouts:
        print(f"Only in workspace: {sorted(actual_checkouts - expected_checkouts)}")
        print(f"Only in manifest: {sorted(expected_checkouts - actual_checkouts)}")
        return 1
    for name, metadata in wanted.items():
        if not metadata["description"].strip():
            print(f"{name}: description is empty")
            return 1
        if not metadata.get("checkout", True):
            continue
        has_page = (WORKSPACE_ROOT / name / "index.html").is_file()
        expected_homepage = PRODUCTION_HOMEPAGES.get(
            name,
            f"https://getcolors.github.io/{name}/" if has_page else "",
        )
        if metadata["homepage"] != expected_homepage:
            print(f"{name}: homepage {metadata['homepage']!r} should be {expected_homepage!r}")
            return 1

    current_rows = json.loads(
        run("gh", "repo", "list", ORG, "--limit", "200", "--json", "name,description,homepageUrl")
    )
    current = {row["name"]: row for row in current_rows}
    if set(current) != set(wanted):
        print(f"Only on GitHub: {sorted(set(current) - set(wanted))}")
        print(f"Only in manifest: {sorted(set(wanted) - set(current))}")
        return 1

    differences = []
    for name, metadata in sorted(wanted.items()):
        actual = current[name]
        fields = {
            "description": ((actual.get("description") or ""), metadata["description"]),
            "homepage": ((actual.get("homepageUrl") or ""), metadata["homepage"]),
        }
        changed = {field: values for field, values in fields.items() if values[0] != values[1]}
        if not changed:
            continue
        differences.append((name, changed))
        if args.apply:
            subprocess.run(
                [
                    "gh", "repo", "edit", f"{ORG}/{name}",
                    "--description", metadata["description"],
                    "--homepage", metadata["homepage"],
                ],
                check=True,
            )
            print(f"updated {ORG}/{name}")
        else:
            for field, (actual_value, wanted_value) in changed.items():
                print(f"{ORG}/{name} {field}: {actual_value!r} != {wanted_value!r}")

    if differences and not args.apply:
        print(f"{len(differences)} repositories differ; rerun with --apply")
        return 1
    print(f"GitHub metadata matches repositories.json for all {len(wanted)} repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
