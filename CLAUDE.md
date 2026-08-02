# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

`~/code/getcolors` is a **workspace, not a repository**. It has no `.git` of its
own; each subdirectory is a separate clone of `git@github.com:getcolors/<name>`.
Nothing here builds as a whole and there is no root manifest, task runner, or
test command.

Every checkout has its own `CLAUDE.md` and most have a `README.md`. **Read the
one for the directory you are working in** — this file only covers what spans
repositories and what a reader of any single one would not know.

## Repository map

The stack is four layers. An arrow means "is built on and pins by git SHA".

```text
SDK            green ──┬── once ──┬── once-colors        (OCI VM, www.getcolors.ai)
(engine)       red   ──┤ (3 colours)
               blue  ──┘          │
                                  ├── walter  ── walter-oci        (OCI dev machine)
               green ─────────────┼── airflow    ── airflow-digitalocean
                                  ├── k3s        ── k3s-hetzner       (Hetzner K3s)
                                  └── clickhouse ── clickhouse-hetzner (Hetzner data stack)
```

**SDK — the workflow engine, three implementations of one model.**

| Repo | Runtime | Notes |
|---|---|---|
| `green/` | Clojure / Babashka | **canonical**; spec in `index.html` |
| `red/` | TypeScript / Bun | spec in `SPEC.md` |
| `blue/` | Python / uv | behavioural port of green |

A step is `opts -> opts`; a workflow is a `wire-fn` graph plus a dynamic
`next-fn`; behaviour is layered with Emacs-`nadvice`-style advice; OpenTofu and
Ansible are event-aware steps. The three use the same key names under their own
engine namespace (`:green/exit` → `"red/exit"` → `"blue/exit"`).

**Packages — agent-installable CLIs ("Package Skills") on the SDK.**

| Repo | Colours | What it provisions |
|---|---|---|
| `once/` | green, red, blue | Basecamp ONCE single-server PaaS |
| `walter/` | green only | one remote development machine (+`stop`/`start`) |
| `airflow/` | green only | one Apache Airflow server |
| `k3s/` | green only | one Hetzner K3s + Flux node |
| `clickhouse/` | green only | three ClickHouse/Keeper nodes + Metabase on Hetzner |

**Deployments — desired state only, no source code.** `once-colors/`,
`walter-oci/`, `airflow-digitalocean/`, `k3s-hetzner/`,
`clickhouse-hetzner/`. Each holds a
`colors.yml`, an installed launcher, `.envrc`, and `devenv.nix`; everything else
is generated (`.colors/`) or secret (`.envrc.private`).

**Applications — container images the deployments run.** `colors-website/`
(Astro landing page for www.getcolors.ai), `colors-redirect/` (Caddy 301 for the
apex), `k3s-helloworld/` (the public GitOps fixture `k3s-hetzner` reconciles).

**`workspace/`** — the tracked GitHub Pages portfolio/readiness audit for this
multi-repository workspace; it is documentation, not a build root.

**`skills/`** — machine-level agent skills (currently `refresh-oci-token`),
installed by hand into `~/.claude/skills/`. Unrelated to Package Skills; see its
`CLAUDE.md`.

## Two name collisions worth knowing before you read anything

- `once/green/`, `once/red/`, `once/blue/` are the **ONCE package** in three
  languages. The **SDK** repositories are the sibling `green/`, `red/`, `blue/`
  checkouts. Instructions in one are not instructions for the other.
- "Skill" means two unrelated things: a Package Skill (`package-once-green`,
  `package-walter-green`, …, installed into a project with `npx skills add`,
  SHA-pinned, recorded in `skills-lock.json`) and a machine skill (`skills/`,
  copied into `~/.claude/skills/`, no pin, no lockfile).

## Commands

Each repo, from its own directory:

| Repo | Test / check |
|---|---|
| `green/` | `bb test` · `clojure -X:test` (one ns: `clojure -X:test :nses '[green.advice-test]'`) |
| `red/` | `bun test` · `bun run typecheck` |
| `blue/` | `uv sync && uv run pytest` (one test: `-k <name>`) |
| `once/` | per-colour suites, then `./scripts/parity.sh` and `./scripts/launcher.sh` |
| `walter/`, `airflow/`, `k3s/`, `clickhouse/` | `bb test` · `bb golden` · `bb golden:accept` · `./scripts/launcher.sh` |
| `colors-website/` | `pnpm typecheck` · `pnpm build` · `pnpm dev` |
| `colors-redirect/` | `caddy validate --config Caddyfile --adapter caddyfile` |

Deployment repos have no test suite. Their commands are the launcher itself:

```sh
./green build              # render .colors/<profile>/ — no provider calls, no credentials
./green create --dry-run   # walk the DAG, skip every side effect
./green create             # converge for real
./green delete             # guarded; see below
```

`build` and `--dry-run` work on a fresh checkout with an empty environment, which
makes them the safe way to check a `colors.yml` edit. Exit code 2 means
validation or usage failure and lists every problem at once. The launcher walks
up from the working directory to find `colors.yml`, so any subdirectory works.
Package repos run the same verbs against their own checkout as `bb green build`
(`bb walter build` in `walter/`; `./green build` in `clickhouse/`).

Toolchains come from `devenv` via `direnv` — run `direnv allow` once per
deployment checkout. `blue/` is the exception and expects its tools on `PATH`.

## Cross-cutting conventions

These hold in every package and deployment; do not relitigate them per repo.

- **`colors.yml` is the only file you edit.** Keys are kebab-case and it holds
  **non-secret values only**.
- **Credentials are `COLORS_PAR_<UPPER_SNAKE_KEY>` environment variables**,
  overlaid onto the matching flat key at run time. One namespace shared by all
  three colours — no per-colour prefix. They live in the gitignored
  `.envrc.private`, never in `colors.yml`, generated output, or documentation.
  OCI is the exception: it authenticates from `~/.oci/config`.
- **Never export `COLORS_PAR_PROFILE`.** `profile` is what keys remote state
  (`<profile>/<stage>.tfstate`) and separates projects sharing one R2 bucket;
  overlaying it would point one deployment at another's state. The packages
  refuse to run when it is set. That is the guard working — do not work around it.
- **`.colors/` is generated output.** Never edit it, never read it as source,
  never commit it. Change `colors.yml` or the upstream template.
- **`delete` is guarded** by `compute-prevent-destroy: true` in `colors.yml`,
  liftable only with `COLORS_PAR_COMPUTE_PREVENT_DESTROY=false` for one run.
  Never edit the committed flag. Never run a real `create`/`delete` against a
  live deployment without explicit authorization.
- **Deployment `.gitignore`s are `.*` with narrow negations**, so a new dotfile
  is invisible to git until negated. Check `git ls-files` rather than inferring
  what is tracked from the working tree.

## The two coupling mechanisms, and how they fail

**SHA pins.** Every downstream edge is a git SHA, not a version range. A commit
in `green/` is invisible in `once/` until it is pushed *and* the pin moves;
`bb pin` in a package repo stamps its launcher after a push. Never invent or
hand-edit a SHA. To develop across a boundary without pinning, point the launcher
at a working tree: `GREEN_LIB_ROOT`, `RED_LIB_ROOT`, `BLUE_LIB_ROOT`,
`ONCE_LIB_ROOT`, `WALTER_LIB_ROOT`, `CLICKHOUSE_LIB_ROOT`. A change that spans
two repos is two commits in two repos, upstream pushed first.

**Installed launchers are copies, not symlinks.** In a deployment repo, the root
`./green` (or `./walter`) is a copy of `.agents/skills/package-*/…`.
`npx skills update -p` rewrites the payload and leaves the root file alone, so
the project keeps running the old pin while `skills-lock.json` claims the new
one. The copy is not optional:

```sh
npx skills update -p
cp .agents/skills/package-once-green/green green    # and red, blue
```

`npx skills use` does *not* install anything despite the name; the installing
verbs are `add` and `update`. `once-colors` CI diffs root against payload to
catch a skipped copy. The same trap applies to `skills/` → `~/.claude/skills/`.

**Two regression nets guard what nothing upstream promises.** `once/scripts/parity.sh`
feeds one fixture through all three colours and diffs generated trees byte for
byte — a change to shared behaviour lands in green, red, and blue in the same
commit, and passes here or it is not done. `bb golden` in `walter`, `airflow`,
`k3s`, and `clickhouse` diffs every provider variant against committed output;
those packages
consume ONCE internals (its provider registry as data, its compute templates as
classpath resources) across a surface ONCE's own rules leave free to change.
Read a golden diff after a pin bump; never `bb golden:accept` merely to make it
pass.

## Git

Every subdirectory is its own repository, and there is nothing to commit at this
level. Work on the current branch. **Do not commit or push any repository unless
explicitly asked** — a rule every checkout here repeats.
