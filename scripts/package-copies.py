#!/usr/bin/env python3
"""Find drift between the files the workspace standards make every package copy.

Some standards are shared by copy, not by pin: `standards/ssh-config.md` §7
says each package owns its `ssh_config` module and its `ansible-local` play,
and the red packages each carry the same `once.ts` shim for ONCE's unexported
ssh module. A copy that drifts in one package is invisible to that package's
own tests and to every other package's. This script makes the drift visible:
for every copied artifact it collects one file per package, replaces the
package's name in all its spellings with one token, clusters the results by
content, and prints every minority cluster as a diff against the largest one.

    workspace/scripts/package-copies.py            # report, exit 1 on drift
    workspace/scripts/package-copies.py --reference rybbit
                                                   # diff everyone against one package
    workspace/scripts/package-copies.py --only ssh-config
                                                   # one artifact family

Run it from anywhere; it locates the workspace as this file's grandparent.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# Each artifact family: the glob templates that find one file per package
# (`{pkg}` is the package directory; the first template that matches wins, so
# a green-only package with its source at the repository root — redis — is
# found too), whether the family is a GATE (unexpected drift fails the run)
# or a WATCH (drift is reported, never fatal, because the file legitimately
# varies per package), and the variants a gate tolerates, each with the
# reason it is allowed to differ. A variant with no reason is drift.
MULTI_NODE = "multi-node: the block carries one Host stanza per node (a deliberate extension of the standard)"
# The three multi-node plays follow compute-cluster.md §6 (one block, the
# profile as marker, one stanza per ONCE alias) but do not agree with one
# another on the stanza lines — langfuse adds `Port 22` and `ForwardAgent no`,
# the postgres pair renders `IdentityFile {{ ssh_private_key }}` (it has not
# adopted ssh-keypair.md) and carries the §8 one-cycle removal task — so each
# is a named variant rather than one gated cluster. Unifying them is owed and
# would move langfuse's local-play golden, which its live deployment forbade
# in the adoption change.
MULTI_NODE_PLAY = "multi-node play (compute-cluster.md §6): one stanza per ONCE alias; the stanza lines differ per package and their unification is owed"
POSTGRES_CFG = "postgres pair: its own ansible.cfg copy, untouched by the compute-cluster adoption; alignment owed with its ssh-keypair adoption"
MIGRATING = "ssh-config.md §8: still writes the pre-standard package-prefixed marker; the migration is owed"
IN_FLIGHT = "ssh-config.md §8: holds the superseded marker while its migration is in flight"

ARTIFACTS: dict[str, dict] = {
    "ssh-config green": {
        "globs": ["{pkg}/green/src/clj/io/github/getcolors/*/ssh_config.clj",
                  "{pkg}/src/clj/io/github/getcolors/*/ssh_config.clj"],
        "gate": True,
        "variants": {"automq": MULTI_NODE, "langfuse": MULTI_NODE, "n8n": MULTI_NODE, "alice": IN_FLIGHT},
    },
    "ssh-config red": {
        "globs": ["{pkg}/red/src/ssh-config.ts"],
        "gate": True,
        "variants": {"automq": MULTI_NODE, "langfuse": MULTI_NODE, "n8n": MULTI_NODE},
    },
    "ssh-config blue": {
        "globs": ["{pkg}/blue/src/package_*_blue/ssh_config.py"],
        "gate": True,
        "variants": {"automq": MULTI_NODE, "langfuse": MULTI_NODE, "n8n": MULTI_NODE},
    },
    "ssh-config play main.yml": {
        "globs": ["{pkg}/green/src/resources/io/github/getcolors/*/tools/ansible-local/main.yml",
                  "{pkg}/src/resources/io/github/getcolors/*/tools/ansible-local/main.yml"],
        "gate": True,
        "variants": {"automq": MULTI_NODE_PLAY, "langfuse": MULTI_NODE_PLAY,
                     "postgres-agy": MULTI_NODE_PLAY, "postgres-ha": MULTI_NODE_PLAY,
                     "alice": IN_FLIGHT,
                     "airflow": MIGRATING, "k3s": MIGRATING, "k8s": MIGRATING, "walter": MIGRATING},
    },
    "ssh-config play ansible.cfg": {
        "globs": ["{pkg}/green/src/resources/io/github/getcolors/*/tools/ansible-local/ansible.cfg",
                  "{pkg}/src/resources/io/github/getcolors/*/tools/ansible-local/ansible.cfg"],
        "gate": True,
        "variants": {"automq": MULTI_NODE, "postgres-agy": POSTGRES_CFG, "postgres-ha": POSTGRES_CFG},
    },
    "ssh-config play inventory.ini": {
        "globs": ["{pkg}/green/src/resources/io/github/getcolors/*/tools/ansible-local/inventory.ini",
                  "{pkg}/src/resources/io/github/getcolors/*/tools/ansible-local/inventory.ini"],
        "gate": True,
        "variants": {"airflow": MIGRATING, "walter": MIGRATING},
    },
    # The wrappers around ONCE's ssh differ per package by design: which
    # desired-state key takes the machine key depends on the providers the
    # package advertises. Watched so a copy that drifts for another reason is
    # still visible.
    "ssh wrapper green": {
        "globs": ["{pkg}/green/src/clj/io/github/getcolors/*/ssh.clj",
                  "{pkg}/src/clj/io/github/getcolors/*/ssh.clj"],
        "gate": False, "variants": {},
    },
    "ssh wrapper red": {"globs": ["{pkg}/red/src/ssh.ts"], "gate": False, "variants": {}},
    "ssh wrapper blue": {"globs": ["{pkg}/blue/src/package_*_blue/ssh.py"], "gate": False, "variants": {}},
    # The shim exists because ONCE's package.json exports only its index; the
    # interface each package declares is the surface it consumes, so a subset
    # is not drift. Watched until ONCE exports ssh and the shims go.
    "once.ts shim (red)": {"globs": ["{pkg}/red/src/once.ts"], "gate": False, "variants": {}},
}

# ONCE is the upstream, not a copy; the SDKs and the deployments carry none of
# these files. Everything else that matches is a package.
EXCLUDE = {"once", "green", "red", "blue", "workspace", "skills"}


def brand_names(pkg: str) -> set[str]:
    """The product's own spelling (ClickStack, PostHog, SigNoz, NetBird …), as
    the catalog recipe records it, plus the same without spaces."""
    recipe = WORKSPACE / "colors-website" / "recipes" / f"{pkg}.yml"
    if not recipe.exists():
        return set()
    for line in recipe.read_text().splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
            return {name, name.replace(" ", "")} - {""}
    return set()


def name_forms(pkg: str) -> list[str]:
    """Every spelling a package's name takes in its own source, longest first
    so `agent_network_blue` is not left with a stray `_blue`."""
    kebab = pkg
    snake = pkg.replace("-", "_")
    words = pkg.split("-")
    camel = words[0] + "".join(w.capitalize() for w in words[1:])
    pascal = "".join(w.capitalize() for w in words)
    upper = snake.upper()
    title = " ".join(w.capitalize() for w in words)
    forms = {kebab, snake, camel, pascal, upper, title, pkg.capitalize()} | brand_names(pkg)
    return sorted(forms, key=len, reverse=True)


COMMENT = re.compile(r"^\s*(#|;;|//)")


def normalise(text: str, pkg: str, ignore_comments: bool) -> str:
    for form in name_forms(pkg):
        text = re.sub(re.escape(form), "PKG", text)
    if ignore_comments:
        text = "\n".join(l for l in text.splitlines() if l.strip() and not COMMENT.match(l)) + "\n"
    return text


def packages() -> list[str]:
    return sorted(
        p.name
        for p in WORKSPACE.iterdir()
        if p.is_dir() and (p / ".git").exists() and p.name not in EXCLUDE
        and not p.name.endswith(("-vultr", "-digitalocean", "-hetzner", "-oci",
                                 "-colors", "-ubuntu", "-aws", "-azure", "-google",
                                 "-ada", "-liliana", "-many"))
    )


def find(pkg: str, templates: list[str]) -> Path | None:
    for t in templates:
        hits = sorted(WORKSPACE.glob(t.format(pkg=pkg)))
        if hits:
            return hits[0]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reference", help="diff every copy against this package instead of the largest cluster")
    ap.add_argument("--only", help="restrict to artifact families whose name contains this text")
    ap.add_argument("--quiet", action="store_true", help="print only the summary lines")
    ap.add_argument("--strict", action="store_true",
                    help="compare comments and blank lines too (default: code only)")
    args = ap.parse_args()

    drift = 0
    for artifact, spec in ARTIFACTS.items():
        if args.only and args.only not in artifact:
            continue
        templates, gate, variants = spec["globs"], spec["gate"], spec["variants"]
        copies: dict[str, tuple[Path, str]] = {}
        for pkg in packages():
            path = find(pkg, templates)
            if path is None:
                continue
            copies[pkg] = (path, normalise(path.read_text(), pkg, not args.strict))
        if len(copies) < 2:
            continue
        clusters: dict[str, list[str]] = defaultdict(list)
        for pkg, (_, text) in copies.items():
            clusters[text].append(pkg)
        ordered = sorted(clusters.values(), key=lambda ps: (-len(ps), ps))
        if args.reference:
            if args.reference not in copies:
                print(f"{artifact}: {args.reference} has no copy; skipped")
                continue
            base_pkgs = [args.reference]
            base_text = copies[args.reference][1]
        else:
            base_pkgs = ordered[0]
            base_text = copies[base_pkgs[0]][1]
        others = [ps for ps in ordered if copies[ps[0]][1] != base_text]
        unexpected = [ps for ps in others if any(p not in variants for p in ps)]
        if not others:
            print(f"ok    {artifact}: {len(copies)} copies agree ({', '.join(sorted(copies))})")
            continue
        label = "DRIFT" if (gate and unexpected) else ("watch" if not gate else "ok   ")
        if gate and unexpected:
            drift += 1
        print(f"{label} {artifact}: {len(copies)} copies in {len(clusters)} clusters; "
              f"base = {', '.join(base_pkgs)}")
        for ps in others:
            reasons = {variants[p] for p in ps if p in variants}
            if reasons and all(p in variants for p in ps):
                print(f"      variant: {', '.join(ps)} — {'; '.join(sorted(reasons))}")
                continue
            print(f"      differs: {', '.join(ps)}" + ("" if gate else "  (watched)"))
            if not args.quiet:
                a = base_text.splitlines(keepends=True)
                b = copies[ps[0]][1].splitlines(keepends=True)
                sys.stdout.writelines(difflib.unified_diff(
                    a, b, fromfile=f"{base_pkgs[0]} ({artifact})", tofile=f"{ps[0]} ({artifact})", n=1))
                print()
    print()
    if drift:
        print(f"{drift} gated artifact famil{'y' if drift == 1 else 'ies'} drifted; the standard's copy is one file in many places")
        return 1
    print("every gated per-package copy agrees with its siblings or is a named variant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
