# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

`~/code/getcolors` is a **workspace, not a repository**. It has no `.git` of its
own; almost every subdirectory is a separate clone of
`git@github.com:getcolors/<name>`. Nothing here builds as a whole and there is
no root manifest, task runner, or test command.

Two exceptions worth knowing before you assume a directory is a clone you can
push. `rama-aws-deploy/` is a clone of `redplanetlabs/rama-aws-deploy`, a
third-party upstream rather than a `getcolors` repository. And `once-aws/`,
`once-azure/`, `once-google/` and `dotfiles-ubuntu/` have the shape of a
deployment — `colors.yml`, a launcher, generated `.colors/` — but **no `.git` at
all**: they are local-only, and nothing in them is backed up by pushing. Check
for `.git` before promising a change can be committed.

The workspace-root `~/code/getcolors/CLAUDE.md` is a symlink to
`workspace/CLAUDE.md`. Cross-repository instruction changes made through either
path therefore belong to the `workspace/` repository and must be committed and
pushed from there; do not treat the root path as untracked merely because the
workspace root has no `.git`.

Every checkout has its own `CLAUDE.md` and most have a `README.md`. **Read the
one for the directory you are working in** — this file only covers what spans
repositories and what a reader of any single one would not know.

## Repository map

The stack is four layers. An arrow means "is built on and pins by git SHA".

```text
SDK            green ──┬── once ──┬── once-colors          (OCI VM, www.getcolors.ai)
(engine)       red   ──┤           ├── airflow (3 colours) ── airflow-digitalocean
               blue  ──┘           │
               green ──────────────┼── walter    ── walter-oci          (OCI dev machine)
                                   ├── rama      ── rama-digitalocean   (DigitalOcean Rama)
                                   ├── k3s       ── k3s-hetzner         (Hetzner K3s)
                                   ├── k8s       ── k8s-digitalocean    (DigitalOcean Kubernetes)
                                   ├── clickhouse ── clickhouse-hetzner (Hetzner data stack)
                                   └── dotfiles  ─┬─ dotfiles-colors    (this machine's home)
                                                  └─ dotfiles-ubuntu    (local only, no .git)
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
| `airflow/` | green, red, blue | one Apache Airflow server |
| `rama/` | green only | one private single-node Rama cluster |
| `k3s/` | green only | one Hetzner K3s + Flux node |
| `k8s/` | green only | two-node kubeadm Kubernetes on DigitalOcean |
| `clickhouse/` | green only | three ClickHouse/Keeper nodes + Metabase on Hetzner |
| `dotfiles/` | green only | Ubuntu or macOS home configuration on the local machine |

`dotfiles/` is the one package that provisions no infrastructure: it renders a
profile under `.colors/` and copies the managed files into a configured local
target, so its verbs are `build`, `diff` and `create` — there is no `delete`.

**Deployments — desired state only, no source code.** `once-colors/`,
`walter-oci/`, `airflow-digitalocean/`, `rama-digitalocean/`, `k3s-hetzner/`,
`k8s-digitalocean/`, `clickhouse-hetzner/`, `dotfiles-colors/`. Each holds a
`colors.yml`, one or more installed launchers, `.envrc`, and `devenv.nix`;
everything else is generated (`.colors/`) or secret (`.envrc.private`).

Four more directories have exactly this shape but no `.git`, as noted above:
`once-aws/`, `once-azure/`, `once-google/` and `dotfiles-ubuntu/`. Treat them as
deployments for every purpose except version control.

How the launcher gets installed is **not** uniform, so check before relying on
it. `once-colors/`, `k3s-hetzner/`, `k8s-digitalocean/` and `dotfiles-colors/`
track a `skills-lock.json` and an `.agents/skills/package-*/` payload;
`walter-oci/` tracks the payload but no lockfile; `airflow-digitalocean/` and
`rama-digitalocean/` track only the root launcher, with neither. Where there is
no payload there is nothing to diff the root launcher against, so the copy trap
described below cannot be detected there at all.

**Applications — container images and GitOps sources the deployments run.**
`colors-website/` (Astro landing page for www.getcolors.ai), `colors-redirect/`
(Caddy 301 for the apex), `k3s-helloworld/` (the public fixture `k3s-hetzner`
reconciles), and `k8s-helloworld/` (the public Flux source and application
`k8s-digitalocean` reconciles).

**Repository landing pages.** Every tracked root `index.html` uses GA4
measurement ID `G-4VKP1WY4QJ`. Its explicit `page_title` must equal the decoded
HTML `<title>` and remain distinct and stable, so one Analytics property can
separate repositories. Add the same tag when adding a root page; do not add an
`index.html` merely to satisfy this convention.

**`workspace/`** — the tracked GitHub Pages portfolio/readiness audit for this
multi-repository workspace; it is documentation, not a build root.

**`skills/`** — Agent Skills. `refresh-oci-token` renews the shared OCI session,
while `create-package-skill` governs the phased workflow for creating a Package
Skill and its deployment. Use the latter directly with
`npx skills use getcolors/skills@create-package-skill`; only skills that need
persistent local files are copied into `~/.claude/skills/`. They are not Package
Skills themselves. See that repo's `CLAUDE.md` and each skill's `SKILL.md`.

## Two name collisions worth knowing before you read anything

- `once/green/`, `once/red/`, `once/blue/` are the **ONCE package** in three
  languages. The **SDK** repositories are the sibling `green/`, `red/`, `blue/`
  checkouts. Instructions in one are not instructions for the other.
- "Skill" means two unrelated things: a Package Skill (`package-once-green`,
  `package-walter-green`, …, optionally installed into a project with
  `npx skills add`, SHA-pinned, recorded in `skills-lock.json`) and an Agent Skill
  (`skills/`, normally used on demand with `npx skills use`, no library pin or
  desired-state lifecycle).

## Commands

Each repo, from its own directory:

| Repo | Test / check |
|---|---|
| `green/` | `bb test` · `clojure -X:test` (one ns: `clojure -X:test :nses '[green.advice-test]'`) |
| `red/` | `bun test` · `bun run typecheck` |
| `blue/` | `uv sync && uv run pytest` (one test: `-k <name>`) |
| `once/` | per-colour suites, then `./scripts/parity.sh` and `./scripts/launcher.sh` |
| `airflow/` | `cd green && bb test && bb golden` · red/blue suites · `./scripts/parity.sh` · `./scripts/launcher.sh` |
| `walter/`, `rama/`, `k3s/`, `k8s/`, `clickhouse/`, `dotfiles/` | `bb test` · `bb golden` · `bb golden:accept` · `./scripts/launcher.sh` |
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
Package repos run the same verbs through their own launcher (`bb walter build`
in `walter/`; `cd green && bb green build` in `airflow/`; `./green build` in
`k3s/`, `k8s/`, `clickhouse/`, and `dotfiles/`).

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
`ONCE_LIB_ROOT`, `WALTER_LIB_ROOT`, `AIRFLOW_LIB_ROOT`, `K3S_LIB_ROOT`,
`K8S_LIB_ROOT`, `CLICKHOUSE_LIB_ROOT`, `RAMA_LIB_ROOT`. A change that spans two
repos is two commits in two repos, upstream pushed first.

**Installed launchers are copies, not symlinks.** In a deployment repo, the root
`./green` (or `./walter`) is a copy of `.agents/skills/package-*/…`.
`npx skills update -p` rewrites the payload and leaves the root file alone, so
the project keeps running the old pin while `skills-lock.json` claims the new
one. The copy is not optional:

```sh
npx skills update -p
cp .agents/skills/package-once-green/green green    # and red, blue
```

`npx skills use` intentionally does not install anything: it fetches a skill and
prints instructions for an agent, which is the main interface for one-shot Agent
Skills such as `create-package-skill`. The persistent installing verbs are `add`
and `update`. `once-colors` CI diffs root against payload to catch a skipped
launcher copy. Manually installed script-bearing Agent Skills such as
`refresh-oci-token` have the same copy trap under `~/.claude/skills/`.

**Three regression nets guard what dependencies do not promise.**
`once/scripts/parity.sh` feeds one fixture through all three colours and diffs
generated trees byte for byte — a change to shared behaviour lands in green,
red, and blue in the same commit, and passes here or it is not done. Airflow has
its own `scripts/parity.sh` for the same three-colour guarantee. `bb golden` in
`walter`, `airflow`, `rama`, `k3s`, `k8s`, `clickhouse`, and `dotfiles` protects provider
templates, state/resource addresses, and any ONCE internals each package reuses. Read a
golden diff after a pin bump; never `bb golden:accept` merely to make it pass.

## Git

Every subdirectory is its own repository, and there is nothing to commit at this
level. Work on the current branch. **Do not commit or push any repository unless
explicitly asked** — a rule every checkout here repeats.
