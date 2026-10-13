# Workspace instructions

Shared guidance for coding agents working across the getcolors checkouts.

## What this directory is

`~/code/getcolors` is a **workspace, not a repository**. It has no `.git` of its
own; almost every subdirectory is a separate clone of
`git@github.com:getcolors/<name>`. Nothing here builds as a whole and there is
no root manifest, task runner, or test command.

Audit the directories rather than relying on a fixed checkout count or an
exhaustive list here. Packages and deployments are added independently.

The workspace-root `~/code/getcolors/AGENTS.md` is a symlink to
`workspace/AGENTS.md`. Inside `workspace/`, `CLAUDE.md` is a compatibility
symlink to `AGENTS.md`; the workspace root need not have a `CLAUDE.md`.
Changes through the root link belong to the `workspace/` repository. When
committing or pushing is authorized, do so from that repository.

Before working in a checkout, read its `AGENTS.md` and README when present;
read `CLAUDE.md` if it provides additional or legacy instructions. Do not assume
both names exist or create a missing compatibility file. Repository instructions
define implementation details and exceptions to the shared conventions below.

## Repository roles and discovery

Use the actual checkouts to discover available repositories. Use
`workspace/repositories.json` for the organization-wide description/homepage
inventory, and each repository's instructions and README for its current
architecture, providers, dependencies and commands. The inventory can include
repositories that are not cloned on this machine.

- **Workflow SDKs:** `green/` (Clojure/Babashka, canonical), `red/`
  (TypeScript/Bun), and `blue/` (Python/uv) implement the same workflow model.
  A step is `opts -> opts`; workflows combine a `wire-fn` graph with a dynamic
  `next-fn`, layered advice, and event-aware OpenTofu/Ansible steps. Engine keys
  use the corresponding namespace (`:green/exit`, `"red/exit"`, `"blue/exit"`).
- **Packages:** installable CLIs own application behavior and templates.
  Many use the three SDK colours and `colors-compute/`; others have a different
  runtime or scope. AutoMQ has Green, Red and Blue implementations. Valkey is
  Green-only. Current Walter (Google development machines) and Alice
  (DigitalOcean Transmission) are Python controllers using PocketDeploy, not
  the older Green implementations. Context SQL is a Blue package for local
  PostgreSQL-backed agent context. Dotfiles manages local home configuration.
  Read the owning repository before choosing a toolchain or lifecycle command.
- **Deployments:** desired state and installed, pinned launchers, rather than
  application source. Inspect tracked files to identify the configuration,
  skill payload, lockfile and launcher layout. Do not infer the running package
  version from a sibling source checkout; older deployments retain older pins.
- **Applications:** container images, websites and GitOps sources, such as
  `colors-website/`, `colors-redirect/`, `airflow-dags/`, `k3s-helloworld/`
  and `k8s-helloworld/`.
- **Workspace and skills:** `workspace/` owns shared documentation and
  standards; `skills/` owns reusable Agent Skills. Neither is a workspace-wide
  build root.

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
canonical organization-wide description/homepage inventory. This repository
holds durable instructions, standards, and repository metadata. Executable
tooling and its tests belong in the package or library that owns the behavior.
Run the owning repository's checks when changing SSH configuration, compute
dependencies, or package integration. Keep GitHub descriptions and homepages
consistent with `repositories.json`.

## Shared compute and state ownership

`standards/` holds versioned normative cross-package contracts. Shared compute
lives in `colors-compute/`, implemented in Green, Red, and Blue. SDK-based
compute package skills, including ONCE, pin that library directly.
PocketDeploy-based controllers have their own ownership contracts; do not apply
colors-compute internals to them.

The colors-compute v2 API owns provider templates, guarded independent node
lifecycle, normalized results,
separate public-key registrations, and named encrypted SSH resources. The
SDK/caller owns topology, fan-out, joins and resource-scope cleanup. Application
installation and the local SSH config play remain package-owned. Provider
additions within the same API require a dependency bump, not application changes.

**For every Package Skill, adopting colors-compute v2 is a breaking,
greenfield-only implementation for new deployments.** Existing deployments keep
their pinned launchers and remain untouched, including their installed skill
payloads, configuration, keys and state. Updating a package's source or bundled
launchers does not authorize refreshing existing deployments.

No migration, adoption, state-transfer tooling or compatibility layer is needed
for this transition; do not add one. New deployments use fresh identities and
state roots. Require explicit v2 configuration and refuse legacy configuration
rather than interpreting it as v2. Existing deployments continue using the
behavior and ownership contracts of their older immutable pins.

`standards/compute-provider.md` defines provider selection and versioned state
ownership; `standards/compute-cluster.md` defines topology and joined inventory;
`standards/compute-name.md` defines stable names; `standards/ssh-keypair.md` defines
versioned machine-key ownership; and `standards/ssh-config.md` defines the
operator's aliases and scoped authentication. Local SSH configuration completes
before application convergence. Delete removes owned aliases before compute
teardown. V2 compute deletion does not delete SSH authority: destroy all consuming
machines and their separately owned registrations before a separate explicit SSH
resource deletion. Older pinned consumers retain their documented key cleanup.
Application deployment keys remain separate from machine access identities.

V2 SSH authority is an encrypted resource under
`<SDK workdir>/<profile>/ssh/<name>/resource.json` locally or
`<s3-prefix>/<profile>/ssh/<name>/resource.json` remotely. Each resource binds its
own `COLORS_PAR_*` passphrase at runtime. Do not treat local authority as disposable
generated output, write a decrypted key copy, or place private material in compute
state. One temporary agent per workflow scope supplies explicit public IdentityFile
selection and an IdentityAgent socket. Public `identity-<reference-sha256>.pub` caches are disposable
and refreshed from verified authority; the socket expires with the scope. Stop
dependent processes before the agent;
never mutate the operator's agent. For consumers of this v2 authority, a bare
alias outside that scope is not an authentication mechanism.

Package source changes and deployment payload refresh do not transfer live state.
Preserve old ownership and do not point a new empty v2 root at existing resources.
`compute-require-existing-state: true` refuses a first create without compatible
ownership; it does not import resources, transfer local state into R2/S3, or recover
missing SSH authority. Backend changes require a separately reviewed operation or
fresh explicitly authorized resource identities, never a silent state redirect.

`standards/context-skill.md` defines Context Skills, which capture a verified
build and are separate from Package Skills and generic Agent Skills.

## Skills and package names

`once/green/`, `once/red/` and `once/blue/` implement the ONCE package; the
sibling `green/`, `red/` and `blue/` repositories implement the SDKs. Instructions
in one are not instructions for the other.

Package Skills ship pinned application launchers, such as `package-once-green`.
Agent Skills capture agent workflows, such as `skills/create-package-skill`.
Context Skills capture verified builds under `standards/context-skill.md`.
Read the owning repository's instructions and the relevant `SKILL.md`; do not
assume that every skill uses the same installer, directory layout or lifecycle.

## Commands and validation

Run checks from the owning repository, using its current instructions, README
and task definitions. There is no workspace-wide test command. Do not maintain
a duplicate per-repository command matrix here: runtime changes can invalidate it.
In particular, current Walter and Alice use Python/uv checks, not `bb` tasks.

For a deployment configuration edit, use the pinned launcher's documented
render, validation or dry-run command before any authorized live operation.
Traditional SDK launchers commonly provide `./green build` and
`./green create --dry-run`; confirm support and side effects in that deployment's
instructions. Do not assume every package has `build`, `create`, `delete`, the
same exit codes, or the same configuration discovery behavior.

Use the repository's documented environment (`devenv`/`direnv`, uv, Bun or other
required tools). Review non-secret `.envrc` configuration before enabling it;
do not inspect or print private configuration or credentials.

For multi-colour packages, shared behavior must land in all supported colours
and pass the owning package's parity checks. Run its relevant unit, golden and
launcher checks, including fixture axes for providers, state backends and SSH
modes. Review golden differences after dependency changes. Snapshot acceptance
(such as `bb golden:accept`) changes expected output; it is not a validation
command and must never be run merely to make a failing check pass.

## Cross-cutting conventions

Apply these within the owning package's documented configuration and lifecycle
contract; legacy pins and newer controllers can differ.

- **For routine deployment configuration, edit `colors.yml`.** Keys are
  kebab-case and values are non-secret. This does not prohibit authorized
  changes to package source, tests, documentation, or installation metadata.
- **Whenever creating or modifying any `.envrc*` file**, ensure its first line
  is exactly `# -*- mode: sh; -*-`.
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
- **Live lifecycle operations require explicit authorization.** Never run real
  creation, convergence, destruction, or Alice `sync` against a live deployment
  without it. Preserve the pinned package's destruction guard. Conventional
  SDK deployments keep `compute-prevent-destroy: true` committed and allow a
  one-run `COLORS_PAR_COMPUTE_PREVENT_DESTROY=false` override. Current Python
  Alice instead requires explicit `compute-prevent-destroy: false` in YAML and
  ignores the environment override; follow its instructions only within an
  authorized operation. Its `sync` must stop Transmission and complete the final
  checksummed copy before deletion. Never infer a legacy deployment's behavior
  from the current source package.
- **Inspect tracked files and ignore rules.** Many deployment `.gitignore`s
  use `.*` with narrow negations. Check `git ls-files` rather than inferring
  tracking from the working tree; keep credentials and private state ignored.

## The two coupling mechanisms, and how they fail

**SHA pins.** A change to an upstream library is invisible to an immutable
consumer pin until the upstream commit is published and the pin is updated.
Never invent or hand-edit a SHA; use the owning package's pinning procedure
(`bb pin` where provided). When publication is authorized, push upstream first,
then update and verify downstream pins in their own repositories.

For development across repository boundaries, use the documented working-tree
override or editable dependency installation. SDK launchers commonly expose
`GREEN_LIB_ROOT`, `RED_LIB_ROOT`, `BLUE_LIB_ROOT` and package-specific overrides;
Python controllers may use editable dependencies instead. Do not assume an old
override remains supported after a runtime rewrite.

**Installed launchers can be independent copies.** Inspect the actual root
launcher, installed payload and lockfile before an authorized refresh. A skill
update can change its payload while leaving the root launcher on the old pin.
For the traditional ONCE layout, the corresponding copy step is:

```sh
cp .agents/skills/package-once-green/green green    # likewise for red and blue
```

Use the actual deployment's installer and payload path, then compare every
installed root launcher with its payload. Package source launchers may instead
be symlinks. Some deployments have manually copied payloads and no lockfile;
never fabricate a lockfile for a manual copy. Updating source or syncing Git
checkouts does not authorize refreshing deployment payloads or transferring state.
Manually installed Agent Skills with scripts have the same independent-copy risk.

## Git

Each checkout is its own repository; the workspace root has nothing to commit.
Work on the current branch. **Do not commit or push any repository unless
explicitly asked.** Prior authorization recorded in a repository document for
another task does not authorize publication or live operations in the current task.

For a request to sync repositories, discover the actual Git checkouts, fetch
remotes, and fast-forward clean branches with configured upstreams. Preserve
local changes, detached checkouts and diverged branches; report those requiring
attention. Do not reset, automatically stash, rebase, switch branches, or push
as an implicit part of a sync. Syncing repositories does not run deployment
commands or update package pins independently of the fetched commits.
