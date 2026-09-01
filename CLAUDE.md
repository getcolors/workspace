# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

`~/code/getcolors` is a **workspace, not a repository**. It has no `.git` of its
own; almost every subdirectory is a separate clone of
`git@github.com:getcolors/<name>`. Nothing here builds as a whole and there is
no root manifest, task runner, or test command.

The workspace currently contains 71 checkouts, all from the `getcolors` GitHub
organisation. Audit the directories rather than relying on a hard-coded count:
new Package Skills and deployments are added independently.

The workspace-root `~/code/getcolors/CLAUDE.md` is a symlink to
`workspace/CLAUDE.md`. Cross-repository instruction changes made through either
path therefore belong to the `workspace/` repository and must be committed and
pushed from there; do not treat the root path as untracked merely because the
workspace root has no `.git`.

Every checkout but the DAGs-only `airflow-dags` has its own `CLAUDE.md` and
most have a `README.md`. **Read the one for the directory you are working
in** — this file only covers what spans repositories and what a reader of any
single one would not know.

## Repository map

The stack is four layers. An arrow means "is built on and pins by git SHA".

```text
SDK            green ──┬── once ──┬── once-colors          (OCI VM, www.getcolors.ai)
(engine)       red   ──┤           ├── airflow (3 colours) ── airflow-digitalocean
               blue  ──┘           │
               green ──────────────┼── walter    ─┬─ walter-oci        (OCI dev machine)
                                   │              ├─ walter-ada        (OCI dev machine)
                                   │              ├─ walter-liliana    (OCI dev machine)
                                   │              ├─ walter-vultr      (Vultr dev machine)
                                   │              └─ walter-many       (Vultr dev machine, seats)
                                   ├── automq    ─── automq-vultr        (Vultr AutoMQ cluster)
                                   ├── n8n       ─── n8n-vultr           (Vultr n8n on colocated Neon)
                                   ├── alice     ─── alice-digitalocean (ephemeral Transmission)
                                   ├── rama      ─── rama-digitalocean  (DigitalOcean Rama)
                                   ├── k3s       ─── k3s-hetzner        (Hetzner K3s)
                                   ├── k8s       ─── k8s-digitalocean   (DigitalOcean Kubernetes)
                                   ├── clickhouse ─ clickhouse-hetzner  (Hetzner data stack)
                                   ├── clickstack ─ clickstack-vultr   (Vultr observability stack)
                                   ├── dbos      ─── dbos-digitalocean  (DigitalOcean DBOS)
                                   ├── restate   ─── restate-digitalocean (DigitalOcean Restate)
                                   ├── temporal  ─── temporal-digitalocean (DigitalOcean Temporal)
                                   ├── vaultwarden ─ vaultwarden-digitalocean (DigitalOcean Vaultwarden)
                                   ├── github-dwh ── github-dwh-vultr (Vultr GitHub warehouse)
                                   ├── wavehouse ─── wavehouse-vultr (Vultr WaveHouse demo)
                                   ├── netbird (3 colours) ─ netbird-vultr (Vultr NetBird control plane)
                                   ├── agent-network (3 colours) ─ agent-network-vultr (Vultr Agent Network demo)
                                   ├── agent-network-k8s (3 colours) ─ agent-network-k8s-vultr (Vultr VKE Agent Network demo)
                                   ├── agent-network-doks (3 colours) ─ agent-network-doks-digitalocean (DigitalOcean DOKS Agent Network demo)
                                   ├── mysql-agy ─── mysql-agy-digitalocean (DigitalOcean MySQL HA)
                                   ├── mysql-ha  ─── mysql-ha-digitalocean  (DigitalOcean MySQL HA)
                                   ├── postgres-agy ─ postgres-agy-digitalocean (DigitalOcean Postgres HA)
                                   ├── postgres-ha ── postgres-ha-digitalocean  (DigitalOcean Postgres HA)
                                   ├── posthog   ─── posthog-digitalocean  (DigitalOcean PostHog)
                                   ├── rybbit    ─┬─ rybbit-digitalocean   (DigitalOcean Rybbit)
                                   │              └─ rybbit-vultr          (Vultr Rybbit)
                                   ├── signoz    ─── signoz-vultr          (Vultr SigNoz)
                                   ├── umami     ─── umami-digitalocean    (DigitalOcean Umami)
                                   └── dotfiles  ─┬─ dotfiles-colors    (this machine's home)
                                                  └─ dotfiles-ubuntu    (Ubuntu home)
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
| `k3s/` | green, red, blue | one Hetzner K3s + Flux node |
| `k8s/` | green, red, blue | two-node kubeadm Kubernetes on DigitalOcean |
| `clickhouse/` | green, red, blue | three ClickHouse/Keeper nodes + Metabase on Hetzner |
| `clickstack/` | green, red, blue | one ClickStack observability server on Vultr: ClickHouse, MongoDB, the HyperDX OTel collector and UI |
| `alice/` | green only | ephemeral Transmission server on DigitalOcean (+`sync`/`tunnel`) |
| `automq/` | green only | three AutoMQ nodes on Vultr: Kafka 3.9.1 wire protocol with Cloudflare R2 as the storage tier, a public SASL_SSL endpoint, and the KRaft quorum confined to a VPC |
| `dbos/` | green, red, blue | one DBOS TypeScript service with colocated PostgreSQL |
| `restate/` | green, red, blue | one Restate server and TypeScript workflow application |
| `temporal/` | green, red, blue | one Temporal stack and TypeScript worker/application |
| `vaultwarden/` | green, red, blue | one Vaultwarden service with Litestream replication |
| `github-dwh/` | blue only | one GitHub organization warehouse with ClickHouse and PocketBase |
| `wavehouse/` | green, red, blue | one WaveHouse analytics demo: ClickHouse, the WaveHouse gateway, and a live GitHub stats dashboard on Vultr |
| `n8n/` | green only | one n8n workflow automation server on Vultr, backed by a colocated self-hosted Neon (storage/compute-separated Postgres with layers and WAL in R2), behind Caddy with an external task runner |
| `netbird/` | green, red, blue | one self-hosted NetBird control plane on Vultr — Traefik, the combined `netbird-server` (management, signal, relay, STUN), the dashboard, and Authentik as the identity provider |
| `agent-network/` | green, red, blue | one minimal NetBird Agent Network demo on Vultr: a keyless, policy-gated LLM endpoint (private reverse proxy, model allowlist, budget caps) and a network-isolated agent container running headless Claude Code |
| `agent-network-k8s/` | green, red, blue | one NetBird Agent Network demo on Vultr Kubernetes Engine: the gateway on VKE behind a TCP-mode load balancer, an in-cluster kaniko image build, and a two-pod application — the NetBird client in netstack/SOCKS5 mode and a network-isolated agent pod running headless Claude Code |
| `agent-network-doks/` | green, red, blue | one NetBird Agent Network demo on DigitalOcean Kubernetes (DOKS): the gateway behind a TCP-mode regional load balancer, an in-cluster kaniko build pushed to a created-or-adopted DigitalOcean Container Registry, and the two-pod application — the NetBird client in netstack/SOCKS5 mode and a network-isolated agent pod running headless Claude Code |
| `mysql-agy/` | green, red, blue | three-node MySQL Group Replication cluster on DigitalOcean with a reserved-IP endpoint, binary-log archiving to R2, and an automated restore-verification drill |
| `mysql-ha/` | green, red, blue | three-member MySQL Group Replication cluster on DigitalOcean with daily snapshots, continuous binary-log archiving to R2, and a scheduled verified restore |
| `postgres-agy/` | green, red, blue | three-node PostgreSQL 17 Patroni failover cluster on DigitalOcean with colocated etcd, HAProxy routing, and pgBackRest backups to R2 |
| `postgres-ha/` | green, red, blue | three-node Patroni PostgreSQL failover cluster on DigitalOcean with quorum synchronous replication, an HAProxy endpoint, and pgBackRest point-in-time recovery to R2 |
| `posthog/` | green, red, blue | one single-node PostHog product analytics suite on DigitalOcean (a ten-container Compose stack, none optional) |
| `rybbit/` | green, red, blue | one single-node Rybbit analytics service (PostgreSQL + ClickHouse) on DigitalOcean or Vultr |
| `signoz/` | green, red, blue | one single-node SigNoz observability stack on Vultr: ClickHouse/Keeper, a Postgres metastore, the SigNoz app, and the OTel collector behind Caddy |
| `umami/` | green, red, blue | one single-node Umami web analytics service with colocated PostgreSQL on DigitalOcean |
| `dotfiles/` | green only | Ubuntu or macOS home configuration on the local machine |

`dotfiles/` is the one package that provisions no infrastructure: it renders a
profile under `.colors/` and copies the managed files into a configured local
target, so its verbs are `build`, `diff` and `create` — there is no `delete`.

**Deployments — desired state only, no source code.** `once-colors/`,
`once-aws/`, `once-azure/`, `once-google/`, `once-vultr/`, `walter-oci/`,
`walter-ada/`, `walter-liliana/`, `walter-vultr/`, `walter-many/`,
`airflow-digitalocean/`, `alice-digitalocean/`, `automq-vultr/`,
`rama-digitalocean/`,
`k3s-hetzner/`, `k8s-digitalocean/`, `clickhouse-hetzner/`, `clickstack-vultr/`,
`dbos-digitalocean/`, `restate-digitalocean/`, `temporal-digitalocean/`,
`vaultwarden-digitalocean/`, `github-dwh-vultr/`, `wavehouse-vultr/`,
`n8n-vultr/`, `netbird-vultr/`, `agent-network-vultr/`, `agent-network-k8s-vultr/`,
`agent-network-doks-digitalocean/`,
`mysql-agy-digitalocean/`,
`mysql-ha-digitalocean/`, `postgres-agy-digitalocean/`,
`postgres-ha-digitalocean/`, `posthog-digitalocean/`, `rybbit-digitalocean/`,
`rybbit-vultr/`, `signoz-vultr/`, `umami-digitalocean/`,
`dotfiles-colors/`, and `dotfiles-ubuntu/`. Each holds a `colors.yml`, one or
more installed launchers, `.envrc`, and `devenv.nix`; everything else is
generated (`.colors/`) or secret (`.envrc.private`).

Every current deployment tracks an `.agents/skills/package-*/` payload, but
launcher provenance is **not** uniform. The five ONCE deployments, Airflow,
Rama, K3s, K8s, DBOS, Restate, Temporal, GitHub DWH, WaveHouse, ClickStack,
NetBird, Agent Network, Agent Network K8s, Agent Network DOKS, Walter Vultr, Walter Many, both MySQL and both
Postgres deployments, Rybbit Vultr, SigNoz, and both dotfiles deployments
also track `skills-lock.json`. Alice, the three OCI Walter deployments, ClickHouse,
Vaultwarden, PostHog, Rybbit DigitalOcean, and Umami track hand-copied
payloads with no lockfile. A lockfile proves an install; never fabricate one
for a manual copy. In every case the root launcher remains a separate copy and
must be compared with the payload after an update.

**Applications — container images and GitOps sources the deployments run.**
`colors-website/` (Astro landing page for www.getcolors.ai), `colors-redirect/`
(Caddy 301 for the apex), `airflow-dags/` (the DAG sources its CI rsyncs to
the Airflow server), `k3s-helloworld/` (the public fixture `k3s-hetzner`
reconciles), and `k8s-helloworld/` (the public Flux source and application
`k8s-digitalocean` reconciles).

**Repository landing pages.** Every tracked root `index.html` carries two
analytics tags: GA4 measurement ID `G-4VKP1WY4QJ`, and the self-hosted Rybbit
snippet
`<script src="https://rybbit.getcolors.ai/api/script.js" data-site-id="9fb9c41a6d49" defer></script>`.
The GA4 `page_title` must equal the decoded HTML `<title>` and remain distinct
and stable, so one Analytics property can separate repositories; Rybbit shares
one site ID across all pages because `getcolors.github.io/<repo>/` paths
already encode the repository. Add both tags when adding a root page; do not
add an `index.html` merely to satisfy this convention.

**`workspace/`** — cross-repository documentation for this multi-repository
workspace; it is documentation, not a build root. `repositories.json` is the
canonical organization-wide description/homepage inventory. Run
`./scripts/github-metadata.py` to check GitHub, and add `--apply` to
synchronize it. `standards/` holds the
normative cross-package conventions: `standards/ssh-keypair.md` defines how a
package generates and owns the profile-named machine SSH keypair in `.ssh/`
(reference implementation: `once`; packages adopt behind their pin flow), and
`standards/ssh-config.md` defines the `~/.ssh/config` block that makes
`ssh <profile>` work (reference implementation: `clickstack`). The two are
siblings and disagree deliberately on two points: the config play is copied per
package rather than shared, and delete removes the config block *before* the
compute destroy while the keypair goes *after* it. `standards/compute-name.md`
defines what a package calls the machines it creates — the profile, with an
optional provider-scoped name key as the override, and no required `package`
key (reference implementation: `alice`, with `netbird` born conforming; every
other package still requires a name key and has yet to migrate).
`standards/context-skill.md` defines the Context Skill — knowledge distilled
from a verified build, the third skill kind beside Package Skills and generic
Agent Skills: five required artifacts, a no-second-copy rule, and spec
validation (reference implementation: `skills/agent-network-single-node`;
consumed by `skills/create-context-skill`, `skills/submit-context-skill`, and
the `colors-website` catalog).

**`skills/`** — Agent Skills. `refresh-oci-token` renews the shared OCI session,
while `create-package-skill` governs the phased workflow for creating a Package
Skill and its deployment. Use the latter directly with
`npx skills use "https://github.com/getcolors/skills" --skill
"create-package-skill"`; only skills that need
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
| `airflow/`, `netbird/`, `agent-network/`, `agent-network-k8s/`, `agent-network-doks/`, `k3s/`, `k8s/`, `clickhouse/`, `clickstack/`, `dbos/`, `restate/`, `temporal/`, `vaultwarden/`, `wavehouse/`, `mysql-agy/`, `mysql-ha/`, `postgres-agy/`, `postgres-ha/`, `posthog/`, `rybbit/`, `signoz/`, `umami/` | `cd green && bb test && bb golden` · red/blue suites · `./scripts/parity.sh` · `./scripts/launcher.sh` |
| `walter/`, `rama/`, `alice/`, `automq/`, `dotfiles/` | `bb test` · `bb golden` · `bb golden:accept` · `./scripts/launcher.sh` |
| `github-dwh/` | `uv run pytest` · `./scripts/golden.sh` · `./scripts/launcher.sh` |
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
  liftable only with `COLORS_PAR_COMPUTE_PREVENT_DESTROY=false` for one run in
  the conventional packages. Alice deliberately ignores that override: an
  explicit `delete`, or `sync` only after its final checksummed copy, is the
  authorization boundary. Never edit the committed flag. Never run a real
  `create`/`delete` (or Alice `sync`) against a live deployment without explicit
  authorization.
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
`K8S_LIB_ROOT`, `CLICKHOUSE_LIB_ROOT`, `CLICKSTACK_LIB_ROOT`, `RAMA_LIB_ROOT`, `ALICE_LIB_ROOT`,
`DBOS_LIB_ROOT`, `RESTATE_LIB_ROOT`, `TEMPORAL_LIB_ROOT`, `VAULTWARDEN_LIB_ROOT`,
`WAVEHOUSE_LIB_ROOT`, `NETBIRD_LIB_ROOT`, `AGENT_NETWORK_LIB_ROOT`,
`AGENT_NETWORK_K8S_LIB_ROOT`, `AGENT_NETWORK_DOKS_LIB_ROOT`,
`AUTOMQ_LIB_ROOT`, `N8N_LIB_ROOT`, `NEON_LIB_ROOT`,
`MYSQL_AGY_LIB_ROOT`, `MYSQL_HA_LIB_ROOT`, `POSTGRES_AGY_LIB_ROOT`,
`POSTGRES_HA_LIB_ROOT`, `POSTHOG_LIB_ROOT`, `RYBBIT_LIB_ROOT`,
`SIGNOZ_LIB_ROOT`, `UMAMI_LIB_ROOT`. A change that spans two
repos is two commits in two repos, upstream pushed first.

**Installed launchers are copies, not symlinks.** In a deployment repo, the root
`./green` is a copy of `.agents/skills/package-*/…`.
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
red, and blue in the same commit, and passes here or it is not done. Every
other tri-colour package carries its own `scripts/parity.sh` for the same
three-colour guarantee, diffing that package's own fixture axes (two fixtures
for NetBird and Agent Network; state backends, compute providers, or
SSH-keypair modes elsewhere). `bb golden` in
`walter`, `airflow`, `rama`, `k3s`, `k8s`, `clickhouse`, `clickstack`, `alice`, `dbos`,
`restate`, `temporal`, `vaultwarden`, `github-dwh`, `wavehouse`, `netbird`,
`automq`, `n8n`,
`agent-network`, `agent-network-k8s`, `agent-network-doks`, `mysql-agy`, `mysql-ha`, `postgres-agy`, `postgres-ha`,
`posthog`, `rybbit`, `signoz`, `umami`, and `dotfiles` protects provider
templates, state/resource addresses, and any ONCE internals each package reuses.
`clickstack`, `signoz`, `netbird`, and `agent-network` render two fixtures
rather than one, because the SSH
Keypair Standard has two modes and conformance means both keygen and opt-out
hold; `rybbit` also renders two, one per compute provider. Read a
golden diff after a pin bump; never `bb golden:accept` merely to make it pass.

## Git

Every subdirectory is its own repository, and there is nothing to commit at this
level. Work on the current branch. **Do not commit or push any repository unless
explicitly asked** — a rule every checkout here repeats.
