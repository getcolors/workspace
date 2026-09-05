# SSH Keypair Standard for Package Skills

Status: normative. Reference implementation: `once` (green, red, blue).
Consumers: every Package Skill that provisions compute. `dotfiles`, which
provisions no infrastructure, and `no-infra` compute are out of scope. No
machine, no key. Every consumer of `compute-cluster.md` — `automq`,
`langfuse`, `mysql-agy`, `mysql-ha`, `postgres-agy`, `postgres-ha`, `k8s` —
delegates to ONCE's `ssh` namespace rather than carrying a copy (the last
five adopted on 2026-09-05, tri-colour).

This document defines how a Package Skill creates, uses, protects, and
destroys the SSH keypair that gives a deployment access to the machines it
provisions. It exists because key provenance used to be per-deployment
folklore. Some deployments generated keys, some referenced hand-registered
account keys, and none agreed on names, locations, or error behaviour.

## 1. The deployment owns its key by default

When the selected compute provider's machine-key configuration key (§4) is
**absent** from `colors.yml`, the package is in keygen mode and MUST manage
the machine-access keypair itself:

- On the first real `create`, generate an ed25519 keypair with no passphrase
  and comment `<profile> managed by Colors`:

  ```sh
  ssh-keygen -q -t ed25519 -N "" -C "<profile> managed by Colors" -f ~/.ssh/<profile>
  ```

- The package names the keypair after the profile, the same value that keys
  remote state (`<profile>/<tool>.tfstate`) and separates deployments sharing
  one provider account. Where the provider holds a key resource, that resource
  is named `<profile>` too (§4.3).

When the provider's machine-key configuration key is **present** in
`colors.yml`, the package is in opt-out mode. It MUST use the supplied value
exactly as it did before this standard, and MUST NOT generate, validate, or
delete any key material. Presence of the explicit key is the only switch.
There is no flag.

## 2. The `~/.ssh` location

All SSH state of a deployment lives in the operator's `~/.ssh`, named by
profile: the private key `~/.ssh/<profile>`, the public key
`~/.ssh/<profile>.pub`, and any per-deployment `known_hosts` a package needs,
as `~/.ssh/<profile>.known_hosts`. Packages MUST NOT create subdirectories
under `~/.ssh`, or keep SSH state inside the checkout.

The profile is what makes one flat shared directory safe. It is globally
unique by construction, because it already keys remote state
(`<profile>/<stage>.tfstate`) in a shared backend. Two deployments cannot
collide in `~/.ssh` without already colliding in state.

- The keypair is not generated output. It must survive regeneration of the
  workdir (`.colors/`), because losing it means losing access to the machine.
  Never write it inside the workdir.
- `~/.ssh` sits outside every checkout. No `.gitignore` interaction, and no
  way for a commit, tarball, or rsync of the repository to sweep key material
  along with it. It is also one predictable place to copy credentials from
  when moving between workstations. The corollary is that a checkout carries
  no key material, so cloning a deployment repository on another workstation
  does not carry access with it. Copy `~/.ssh/<profile>`(`.pub`) deliberately
  when access should move.
- The package MUST enforce permissions on every real run, not only at
  generation time: `700` on `~/.ssh`, creating it if missing, and `600` on the
  private key. A key restored with wrong permissions then fails early and
  clearly.
- `build` and `--dry-run` MUST NOT read, create, or require anything under
  `~/.ssh`. Builds render from desired state alone and stay byte-deterministic
  (§6).

## 3. Lifecycle and error conditions

Key lifecycle belongs to `create` and `delete` alone. Verbs like `stop`,
`start`, `run`, and `sync` MUST NOT touch key material.

### 3.1 Create

On a real `create` in keygen mode, before any provider call:

| Compute state | `~/.ssh/<profile>` | Meaning | Behaviour |
|---|---|---|---|
| readable, non-empty | present | normal converge | reuse the key |
| readable, non-empty | absent | this workstation does not hold the key (fresh clone, new machine) | error. Access to the live machine is lost; do not regenerate |
| absent / unreadable | present | previous delete incomplete, or interrupted first create | error. Refuse (§3.2) |
| absent / unreadable | absent | first create | generate |

"Compute state" is the deployment's own OpenTofu state for the compute stage,
read best-effort. A state that cannot be read, on a fresh clone before any
build or with a missing backend, counts as absent. That makes the fourth row
reachable on a fresh clone whose remote state does exist. The
`prevent_destroy` guard on the compute resource catches that case, and the
apply fails loudly instead of replacing the instance.

### 3.2 Never overwrite, never adopt

An existing `~/.ssh/<profile>` without state MUST be an error, never silently
overwritten. The key on disk may be the only remaining credential to a host
that is still alive. The error message MUST give the recovery path and make
the human the authorization boundary:

> verify at the provider that no host for `<profile>` survives; if the
> previous create was interrupted before creating resources, or the host is
> confirmed gone, remove `~/.ssh/<profile>` and `~/.ssh/<profile>.pub` and
> retry.

Symmetrically, a provider-side key resource named `<profile>` that is not in
the deployment's state MUST be an error, never auto-imported (§5). If state
was lost, the instance is probably orphaned too, and importing the key would
let `create` build a second machine beside the first.

### 3.3 Delete

In keygen mode, a real `delete` removes the local keypair **last, only after
the compute destroy succeeded**. A delete that fails or is interrupted leaves
the key in place, correctly, because it is still needed. That ordering is what
holds the invariant "the key exists exactly when the deployment does", and
what gives §3.1 its meaning. The removal touches the profile-named files and
nothing else. `~/.ssh` itself is the operator's directory and is never
removed. Dry-run deletes touch nothing.

### 3.4 Rotation

There is no rotation verb. Machine key lists are ForceNew on the providers
that register keys, so rotation is a rebuild: `delete`, then `create`.

## 4. How providers take the public key

Providers take the public key in three ways. This standard covers all three,
and a package implements the ways its own providers use.

### 4.1 Path providers (OCI, AWS, Azure, Google)

The template reads the public key with `file(<path>)`. In keygen mode the
package fills the provider's machine-key configuration key with the absolute
path of `~/.ssh/<profile>.pub`, expanding `$HOME` itself. Tofu's `file()` does
not expand `~`, and it resolves relative paths against the stage directory.

### 4.2 Content providers (Yandex)

The template interpolates the public key content (`compute-pubkey`). In keygen
mode the package fills it with the content of `~/.ssh/<profile>.pub` on real
events, and with the fixed placeholder
`ssh-ed25519 PLACEHOLDER managed-by-colors` on `build` and `--dry-run` (§6).

### 4.3 Registered-key providers (DigitalOcean, Hetzner, Vultr, AWS)

The account holds a key resource, and instances reference it. In keygen mode
the package's compute template creates that resource itself, named
`<profile>`, from the public key file, and references it by resource
attribute, never by a literal id:

```hcl
resource "vultr_ssh_key" "machine" {
  name    = "<profile>"
  ssh_key = fileexists("<abs path>") ? trimspace(file("<abs path>")) : "ssh-ed25519 PLACEHOLDER managed-by-colors"
}
```

The `fileexists` guard is not decoration. A delete after a completed delete
renders this stack with the key files already removed — §3.3 removes them
last — and tofu evaluates `file()` while planning the destroy of an empty
state, so an unguarded read turns the second delete into a template error.
A real create has generated the file in preflight (§3) before the stack
renders, so the fallback is never applied; a build renders the placeholder
path and never reads it. The fallback is the §4.2 placeholder line rather
than an empty string because the provider validates the attribute at plan
time (DigitalOcean refuses an empty `public_key` even while destroying
nothing), and it is not key material the provider would accept at apply. (Found live on 2026-09-05 by the
multi-node adopters' second-delete gate; their templates carry the guard.
ONCE's DigitalOcean, Hetzner and Vultr templates, and the single-node
packages that render them or copy the line — `signoz`, `clickstack`,
`posthog`, `redis`, `agent-network`, `netbird` and the rest — still read
the file unguarded and owe the same one-line change.)

The resource lives in the deployment's state, which is what makes ownership
decidable (§5). In opt-out mode the template keeps today's literal references
and creates nothing.

AWS is both a path provider, since the key arrives as a `file()` path, and a
registered-key provider through `aws_key_pair`. In keygen mode its `key_name`
MUST be `<profile>`. In opt-out mode it keeps its historical name.

## 5. Ownership and the collision preflight

The deployment's OpenTofu state decides whether a provider-side key resource
belongs to it: the resource id recorded under `<profile>/<stage>.tfstate` in
the shared backend. Names are conventions anyone can copy. A fingerprint
identifies key material, not which deployment created it. The id in state is
the link the provider itself made. No fingerprint or ownership record is ever
written into `colors.yml`, because desired state is hand-written input, not
observed output.

On a real `create` in keygen mode, for providers with a simple token-bearing
REST API (DigitalOcean, Hetzner, Vultr), the package MUST check for an account
key named `<profile>` before applying:

- found, and its id is the one in our state → normal converge.
- found, id not in our state, whether state is absent or different → error,
  and the local public key's fingerprint selects the message:
  - fingerprint matches `~/.ssh/<profile>.pub` → our leftover. The message
    directs the operator to verify no host survives, delete the provider key,
    and retry.
  - fingerprint differs → foreign key. The message MUST say **do not delete
    it**, and direct the operator to investigate or change profile.
- not found → proceed.

AWS is exempt from the REST preflight. `aws_key_pair` names are unique per
region and the instance depends on the key pair, so a duplicate name fails the
apply loudly before any instance exists. Path and content providers have no
account resource and so have nothing to collide with. Only the local checks
apply to them.

The preflight runs on a real `create` alone, so `build` and `--dry-run` stay
credential-free. Packages MUST follow pagination. A preflight API failure is
an error, not a skip.

## 6. Build determinism and parity

`build` and `--dry-run` MUST render byte-identically whether or not the
keypair exists, and identically across colours:

- Path values (§4.1) come from the home directory and the profile, and are
  never read from disk. A package that commits rendered build output, as
  walter's goldens do, substitutes a stable placeholder for the home directory
  on `build`, so the committed bytes match across workstations.
- Content values (§4.2) use the fixed placeholder on non-real events.
- Generation, permission enforcement, the state matrix (§3.1), and the
  preflight (§5) run on real events alone.

Multi-colour packages MUST land the whole behaviour in every colour in one
commit, and cover it with their parity fixtures.

## 7. Only the generated key

In keygen mode the generated key is the machine's only access key. The package
MUST NOT merge additional operator keys into the instance's key list. Personal
access goes through the deployment's key. Opt-out mode passes the user's
explicit list through untouched, as it does today.

## 8. Adoption

- New packages are born conforming. `create-package-skill` references this
  document.
- Existing packages adopt behind their normal pin flow. Existing deployments
  keep working unchanged, because their `colors.yml` already carries explicit
  keys, which is exactly opt-out mode. A live deployment adopts keygen mode
  only by rebuild.
- This standard supersedes walter's `compute-keygen` flag, which goes when
  walter adopts. Walter's per-provider machine-key keys then follow the
  opt-out rule like everyone else's.
- A package that used to take a private-key path beside the account key
  (`digitalocean-ssh-private-key` in the MySQL and PostgreSQL pairs) keeps
  it as an opt-out-only key: required when `digitalocean-ssh-keys` is
  supplied and unused otherwise, because in keygen mode the identity file
  is `~/.ssh/<profile>` by §2 and nothing else names it.
- A package whose historical key was not the §4 machine-key key (`k8s` took
  `digitalocean-ssh-key-fingerprint`) renames it to the §4 key and refuses
  the old name by name in `state-errors`: an operator sees the rename,
  rather than an unchanged `colors.yml` silently selecting keygen mode.
- Delete removes the key files after the compute destroy and MUST fail the
  run when one survives the removal: a `delete` that reports success with
  `~/.ssh/<profile>` still on disk turns the next create's §3.2 refusal into
  a puzzle. ONCE's `cleanup-step` does so since 31d3758.

## 9. Conformance checklist

A package conforms when:

1. Absent machine-key config means keygen mode, and present means opt-out with
   byte-for-byte historical rendering.
2. The key is ed25519, has no passphrase, carries the comment
   `<profile> managed by Colors`, and sits at `~/.ssh/<profile>`(`.pub`).
3. `700` and `600` are enforced on every real run.
4. The §3.1 matrix is implemented with the §3.2 messages.
5. The provider resource is named `<profile>`, referenced by attribute, and
   lives in deployment state.
6. The REST preflight covers DigitalOcean, Hetzner, and Vultr, with
   fingerprint-selected messages.
7. Delete removes the local key last, after a successful destroy, and failed
   deletes leave it.
8. `build` and `--dry-run` are deterministic and credential-free, and never
   touch `~/.ssh`.
9. No extra keys are merged in keygen mode.
10. Goldens and parity fixtures are updated in the same change.
11. A second `delete` after a completed one exits 0 and changes nothing: the
    key resource's template read is guarded with `fileexists` (§4.3) and the
    delete tolerates an empty state.
