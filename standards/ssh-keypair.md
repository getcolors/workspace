# SSH Keypair Standard for Package Skills

Status: normative. Reference implementation: `once` (green, red, blue).
Consumers: every Package Skill that provisions compute. `dotfiles` (no
infrastructure) and `no-infra` compute are out of scope: no machine, no key.

This document defines how a Package Skill creates, uses, protects, and
destroys the SSH keypair that gives a deployment access to the machines it
provisions. It exists because key provenance used to be per-deployment
folklore: some deployments generated keys, some referenced hand-registered
account keys, and none agreed on names, locations, or error behaviour.

## 1. Default behaviour: the deployment owns its key

When the selected compute provider's machine-key configuration key (§4) is
**absent** from `colors.yml`, the package is in **keygen mode** and MUST
manage the machine-access keypair itself:

- On the first real `create`, generate an ed25519 keypair with no passphrase
  and comment `<profile> managed by Colors`:

  ```sh
  ssh-keygen -q -t ed25519 -N "" -C "<profile> managed by Colors" -f ~/.ssh/<profile>
  ```

- The keypair is named after the **profile**, the same value that keys remote
  state (`<profile>/<tool>.tfstate`) and separates deployments sharing one
  provider account. Where the provider holds a key resource, that resource is
  also named `<profile>` (§4.3).

When the provider's machine-key configuration key **is present** in
`colors.yml`, the package is in **opt-out mode**: it MUST use the supplied
value exactly as before this standard and MUST NOT generate, validate, or
delete any key material. Presence of the explicit key is the only switch;
there is no flag.

## 2. The `~/.ssh` location

All SSH state of a deployment lives in the operator's `~/.ssh`, named by
profile: the private key `~/.ssh/<profile>`, the public key
`~/.ssh/<profile>.pub`, and any per-deployment `known_hosts` a package needs
(as `~/.ssh/<profile>.known_hosts`). Packages MUST NOT create subdirectories
under `~/.ssh` or keep SSH state inside the checkout.

The profile is what makes a shared flat directory safe: it is globally unique
by construction, because it already keys remote state
(`<profile>/<stage>.tfstate`) in a shared backend. Two deployments cannot
collide in `~/.ssh` without already colliding in state.

- The keypair is **not** generated output. It must survive regeneration of
  the workdir (`.colors/`); losing it means losing access to the machine.
  Never write it inside the workdir.
- `~/.ssh` is outside every checkout: no `.gitignore` interaction, no way for
  a commit, tarball, or rsync of the repository to sweep key material along —
  and one predictable place to copy credentials from when moving between
  workstations. The corollary: a checkout carries no key material, so cloning
  a deployment repository on another workstation does not carry access with
  it. Copy `~/.ssh/<profile>`(`.pub`) deliberately when access should move.
- The package MUST enforce permissions on every real run, not only at
  generation time: `700` on `~/.ssh` (creating it if missing), `600` on the
  private key. A key restored with wrong permissions fails early and clearly.
- `build` and `--dry-run` MUST NOT read, create, or require anything under
  `~/.ssh`. Builds render from desired state alone and stay
  byte-deterministic (§6).

## 3. Lifecycle and error conditions

Key lifecycle belongs to `create` and `delete` only. Verbs like `stop`,
`start`, `run`, `sync` MUST NOT touch key material.

### 3.1 Create

On a real `create` in keygen mode, before any provider call:

| Compute state | `~/.ssh/<profile>` | Meaning | Behaviour |
|---|---|---|---|
| readable, non-empty | present | normal converge | reuse the key |
| readable, non-empty | absent | this workstation does not hold the key (fresh clone, new machine) | **error**: access to the live machine is lost; do not regenerate |
| absent / unreadable | present | previous delete incomplete, or interrupted first create | **error**: refuse (§3.2) |
| absent / unreadable | absent | first create | generate |

"Compute state" is the deployment's own OpenTofu state for the compute stage,
read best-effort; a state that cannot be read (fresh clone before any build,
missing backend) counts as absent. This makes the fourth row reachable on a
fresh clone whose remote state actually exists — the `prevent_destroy` guard
on the compute resource is the net that catches that case: the apply fails
loudly instead of replacing the instance.

### 3.2 Never overwrite, never adopt

An existing `~/.ssh/<profile>` without state MUST be an error, never silently
overwritten: the key on disk may be the only remaining credential to a host
that is still alive. The error message MUST give the recovery path and make
the human act the authorization boundary:

> verify at the provider that no host for `<profile>` survives; if the
> previous create was interrupted before creating resources, or the host is
> confirmed gone, remove `~/.ssh/<profile>` and `~/.ssh/<profile>.pub` and
> retry.

Symmetrically, a provider-side key resource named `<profile>` that is not in
the deployment's state MUST be an error, never auto-imported (§5): if state
was lost, the instance is likely orphaned too, and importing the key would
let `create` build a second machine next to the first.

### 3.3 Delete

In keygen mode, a real `delete` removes the local keypair **last, only after
the compute destroy succeeded**. A delete that fails or is interrupted leaves
the key in place — correctly, because it is still needed. This ordering is
what makes the invariant "key present ⇔ deployment exists" hold, and what
gives §3.1 its meaning. The removal touches exactly the profile-named files;
`~/.ssh` itself is the operator's directory and is never removed. Dry-run
deletes touch nothing.

### 3.4 Rotation

There is no rotation verb. Machine key lists are ForceNew on the providers
that register keys; rotation is a rebuild (`delete`, then `create`).

## 4. Provider shapes

Providers consume the public key in three shapes. The standard covers all
three; a package implements the shapes of the providers it supports.

### 4.1 Path providers (OCI, AWS, Azure, Google)

The template reads the public key with `file(<path>)`. In keygen mode the
package fills the provider's machine-key configuration key with the
**absolute path** of `~/.ssh/<profile>.pub` — `$HOME` expanded by the
package, because tofu's `file()` does not expand `~` and resolves relative
paths against the stage directory.

### 4.2 Content providers (Yandex)

The template interpolates the public key **content** (`compute-pubkey`). In
keygen mode the package fills it with the content of `~/.ssh/<profile>.pub` on
real events, and with the fixed placeholder
`ssh-ed25519 PLACEHOLDER managed-by-colors` on `build`/`--dry-run` (§6).

### 4.3 Registered-key providers (DigitalOcean, Hetzner, Vultr — and AWS)

The account holds a key resource; instances reference it. In keygen mode the
package's compute template creates that resource itself, named `<profile>`,
from the public key file, and references it by resource attribute — never by
a literal id:

```hcl
resource "vultr_ssh_key" "machine" {
  name    = "<profile>"
  ssh_key = trimspace(file("<abs path to ~/.ssh/<profile>.pub>"))
}
```

The resource lives in the deployment's state, which is what makes ownership
decidable (§5). In opt-out mode the template keeps today's literal
references and creates nothing.

AWS is both a path provider (the key arrives as a `file()` path) and a
registered-key provider (`aws_key_pair`). In keygen mode its `key_name` MUST
be `<profile>`; in opt-out mode it keeps its historical name.

## 5. Ownership and the collision preflight

The authority on whether a provider-side key resource belongs to the
deployment is the deployment's **OpenTofu state**: the resource id recorded
under `<profile>/<stage>.tfstate` in the shared backend. Names are
conventions anyone can copy; fingerprints identify key material, not
paternity; the id in state is the link the provider itself created. No
fingerprint or ownership record is ever written into `colors.yml`: desired
state is hand-written input, not observed output.

On a real `create` in keygen mode, for providers with a simple token-bearing
REST API (DigitalOcean, Hetzner, Vultr), the package MUST check for an
account key named `<profile>` before applying:

- found, and its id is the one in our state → normal converge.
- found, id not in our state (state absent or different): **error**, and the
  local public key's fingerprint selects the message:
  - fingerprint matches `~/.ssh/<profile>.pub` → our leftover; the message
    directs the operator to verify no host survives, delete the provider key,
    and retry.
  - fingerprint differs → foreign key; the message MUST explicitly say **do
    not delete it** — investigate, or change profile.
- not found → proceed.

AWS is exempt from the REST preflight: `aws_key_pair` names are unique per
region and the instance depends on the key pair, so a duplicate name fails
the apply loudly before any instance exists. Path/content providers have no
account resource, hence nothing to collide: only the local checks apply.

The preflight runs only on a real `create` — `build` and `--dry-run` stay
credential-free. Pagination MUST be followed; a preflight API failure is an
error, not a skip.

## 6. Build determinism and parity

`build` and `--dry-run` MUST render byte-identically whether or not the
keypair exists, and identically across colours:

- Path values (§4.1) are derived from the home directory and the profile,
  never read from disk. A package that commits rendered build output (walter's
  goldens) substitutes a stable placeholder for the home directory on
  `build`, so the committed bytes are identical across workstations.
- Content values (§4.2) use the fixed placeholder on non-real events.
- Generation, permission enforcement, the state matrix (§3.1), and the
  preflight (§5) run only on real events.

Multi-colour packages MUST land the whole behaviour in all colours in the
same commit and cover it with their parity fixtures.

## 7. Only the generated key

In keygen mode the generated key is the machine's only access key: the
package MUST NOT merge additional operator keys into the instance's key list.
Personal access goes through the deployment's key. (Opt-out mode passes the
user's explicit list through untouched, as today.)

## 8. Adoption

- New packages are born conforming; `create-package-skill` references this
  document.
- Existing packages adopt behind their normal pin flow. Existing deployments
  keep working unchanged: their `colors.yml` already carries explicit keys,
  which is exactly opt-out mode. A live deployment adopts keygen mode only
  by rebuild.
- Walter's `compute-keygen` flag is superseded by this standard and is
  removed when walter adopts it; walter's per-provider machine-key keys
  follow the opt-out rule like everyone else's.

## 9. Conformance checklist

A package conforms when:

1. Absent machine-key config ⇒ keygen mode; present ⇒ opt-out, byte-for-byte
   historical rendering.
2. ed25519, no passphrase, comment `<profile> managed by Colors`, at
   `~/.ssh/<profile>`(`.pub`).
3. `700`/`600` enforced on every real run.
4. The §3.1 matrix implemented with the §3.2 messages.
5. Provider resource named `<profile>`, referenced by attribute, living in
   deployment state.
6. REST preflight for DigitalOcean/Hetzner/Vultr with fingerprint-selected
   messages.
7. Delete removes the local key last, after a successful destroy; failed
   deletes leave it.
8. `build`/`--dry-run` deterministic, credential-free, never touching
   `~/.ssh`.
9. No extra keys merged in keygen mode.
10. Goldens/parity updated in the same change.
