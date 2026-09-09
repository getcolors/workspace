# SSH keypair standard for package skills

Status: normative target, revised 2026-09-09. Shared SSH implementation belongs
to `colors-compute` in Green, Red, and Blue. This revision supersedes ONCE
ownership and the previous single-state create matrix. It does not claim that
existing consumers have migrated.

Consumers: every package skill that creates compute machines. Packages that
create no machines have no keypair requirement. `no-infra` compute is not a
supported selection under [compute-provider.md](compute-provider.md).

## 1. The deployment owns its key by default

When the selected provider's machine-key setting is absent from desired state,
the library MUST manage one deployment access keypair. This is keygen mode.
When that setting is present, the library MUST use the supplied key reference
and MUST NOT generate, adopt, change permissions on, or delete the operator's
key material. This is opt-out mode. A present but invalid setting is a
validation error, not an implicit request to generate a key.

The library registry defines each provider's machine-key setting. Consumers
MUST NOT duplicate the provider-to-setting mapping. Existing opt-out settings
must retain their meaning through migration, including private-key path
references required by downstream SSH clients.

In keygen mode, the first real create generates an ed25519 keypair without a
passphrase and with comment `<profile> managed by Colors`. The key is shared
by the deployment's nodes. Only that generated key is installed for machine
access; extra operator keys MUST NOT be merged into its authorized-key list.
Opt-out mode preserves the supplied list.

## 2. Location and identity

The private key is `~/.ssh/<profile>`, the public key is
`~/.ssh/<profile>.pub`, and an optional deployment known-hosts file is
`~/.ssh/<profile>.known_hosts`. Keys MUST NOT live in the checkout, generated
workdir, or newly created subdirectories under `~/.ssh`.

The profile MUST be unique among deployments managed by the same local SSH
identity. Different buckets or state prefixes do not guarantee that uniqueness.
Local keys and aliases share a namespace even when remote backends differ.
The library MUST detect ownership collisions and refuse adoption.

The library MUST resolve home from `$HOME` first, then the runtime home,
consistently with the local Ansible play. On real create and delete in keygen
mode it MUST enforce `700` on the SSH directory and `600` on the private key
when present. It MUST NOT change unrelated files. Other lifecycle verbs MUST
NOT generate, remove, or change key material.

Build and dry-run MUST NOT read, create, modify, or require local SSH files.
Private key material MUST NOT enter desired state, outputs, logs, or remote
ownership records. Node results may carry an identity path reference only.

## 3. Lifecycle and state

The deployment prepares its key once before node fan-out. Individual node
operations consume its public key or provider registration reference; they
MUST NOT run independent local key generation or cleanup.

### 3.1 Create

Before key generation or provider mutation, the library MUST read the shared
ownership record and recorded node states. Backend credentials are required
for this read. Reads distinguish confirmed absence from failure.

| Recorded ownership | Local keypair | Behavior |
|---|---|---|
| Readable deployment owns nodes or a prepared key | Present and consistent | Reuse the key |
| Readable deployment owns nodes or a prepared key | Missing or inconsistent | Refuse; never regenerate access to an existing deployment |
| Confirmed absent | Any profile key file exists | Refuse adoption and leave files intact |
| Confirmed absent | Neither key file exists | Generate and record preparation before dispatching nodes |
| Unreadable or uncertain | Any state of local files | Refuse before generating or mutating anything |

Consistency includes a complete matching public/private pair and agreement
with recorded public-key identity where available. Legacy ownership without
that identity needs an explicit migration check. An unreadable backend MUST
NOT become the first-create case. A fresh checkout does not establish that
remote resources are absent.

The ownership record MUST distinguish a prepared deployment from one with no
state, so retries after partial node creation can reuse the key. If interruption
leaves local files without a completed ownership record, the next run MUST
refuse automatic adoption. Remote records may contain a public-key fingerprint
and provider registration ids, never private key material.

### 3.2 Never overwrite or adopt implicitly

An existing profile key file without established ownership MUST be an error.
The diagnostic MUST direct the operator to verify whether any host survives
and to resolve the leftover files explicitly. It MUST NOT remove or overwrite
them automatically. A profile key registration belonging to another state
MUST likewise never be auto-imported.

If a local key is missing while owned machines remain, report that this
workstation lacks the deployment key. Recreating a key with the same name
does not restore access. Key transfer or rebuild is an explicit operator action.

### 3.3 Delete

The shared local keypair MUST be removed last, only after all recorded nodes
and owned provider-side key registrations have been successfully destroyed.
A successful individual node delete MUST NOT remove it. A failed or interrupted
delete MUST retain the key and ownership records needed for retry.

Cleanup MUST account for attempted, partially created, and retired nodes from
the deployment record, not current desired count alone. Confirmed empty states
are idempotent cleanup cases. Unreadable state blocks destructive cleanup.

Removal touches only owned profile files, including an owned per-deployment
known-hosts file if one was created. The SSH directory itself is never removed.
A surviving key file after attempted cleanup MUST make delete fail. A repeated
delete after successful cleanup MUST succeed without requiring key files.

### 3.4 Rotation

This contract has no in-place rotation operation. Changing managed machine
keys requires an explicit rebuild. A dependency bump MUST NOT regenerate keys
or silently change the access key mode of an existing deployment.

## 4. Provider adapters and public keys

The library MUST support provider-specific public-key inputs through its
registry and templates. Packages supply access requirements without branching
on provider names.

### 4.1 Path inputs

OCI, AWS, Azure, and Google templates may read the public key from a file.
On real operations the library supplies an absolute path and expands home
itself. Template file functions MUST NOT be expected to expand `~`.

### 4.2 Content inputs

For Yandex content inputs, the library reads the public key only on real
operations. Builds and dry-runs use the fixed fixture
`ssh-ed25519 PLACEHOLDER managed-by-colors` without accessing the filesystem.

### 4.3 Provider-side registrations

DigitalOcean, hcloud, Vultr, and AWS use provider-side key registrations.
In keygen mode the library MUST create each required registration once in
shared deployment state, with the profile as its default name. It MUST record
its provider identity, scope, and resource id. Node states reference that
registration and MUST NOT each create a resource named after the same profile.

Registration scope is provider-specific, such as an AWS region. Deployments
that need more than one scope require one explicitly owned registration per
scope. The same public key may be registered in each scope. An `ssh_key_id`
returned by a node is a reference to that ownership, not ownership itself.

Opt-out mode creates no managed registration for supplied account keys.
Legacy templates that created registrations in opt-out mode require an
explicit ownership migration; they MUST NOT silently delete or abandon them.

Template reads of key files MUST tolerate a repeated delete after files have
been removed. Public-key reads may use a guarded placeholder; private-key
reads for connections must also be guarded. Real create MUST verify its key
before rendering so a placeholder cannot reach a provider apply.

## 5. Collision preflight

Recorded state determines registration ownership. A matching name or public
key fingerprint alone does not establish ownership.

On real create in keygen mode, DigitalOcean, hcloud, and Vultr adapters MUST
check registrations with the intended name, following pagination. A preflight
API failure is an error, not a skipped check.

- A registration whose id and scope match shared ownership may be reused.
- An unowned registration with matching key material is a possible leftover.
  Refuse and require the operator to establish whether any host survives.
- An unowned registration with different material is foreign. Refuse and
  explicitly advise against deleting it.
- No matching registration permits normal creation.

AWS may rely on its scoped key-name uniqueness and the node dependency on
successful registration instead of a separate REST preflight. The library MUST
prove that duplicate registration failure prevents node creation. Providers
without registrations require only the local ownership checks.

Preflight runs once per required registration scope, before node fan-out.
Build and dry-run perform no account checks.

## 6. Determinism and parity

The library MUST own the provider and keypair-mode matrix in all three colors.
Builds MUST render identically whether SSH files exist or not, using a stable
home placeholder and fixed public-key content where needed.

Checks MUST cover the state matrix, unowned files, foreign registrations,
partial creation and retry, shared-key reuse across node calls, failed delete,
and successful repeated delete. All colors MUST agree on ownership decisions
and error behavior. Package tests cover delegation and lifecycle ordering.

## 7. Access references downstream

The node result MUST carry its login and any required identity reference to the
join. Ansible may use an explicit opt-out identity path when configured.
The operator SSH config policy remains in [ssh-config.md](ssh-config.md),
which emits `IdentityFile` and `IdentitiesOnly` only in keygen mode.
Neither consumer may receive private key content in the collected parameters.

## 8. Migration

Moving SSH behavior from ONCE to `colors-compute` MUST preserve existing local
key paths, comments, access modes, and provider registrations unless an explicit
migration changes them. Old per-cluster or per-node registration resources
must transfer ownership into shared state without duplicate management.

Legacy machine-key setting renames MUST be diagnosed by name. They MUST NOT
silently turn opt-out into keygen. Existing deployments adopt a different
access key only through explicit rebuild or a separately specified migration.

Migration evidence MUST include ownership mapping, repeated-delete behavior,
and interrupted-run recovery. Historical provider template exceptions are
migration work, not exemptions from guarded file reads or centralized ownership.

## 9. Conformance checklist

1. The library owns key behavior and provider mappings in all three colors.
2. Keygen and opt-out are explicit consequences of setting presence.
3. One deployment key is prepared before fan-out, outside node operations.
4. Unreadable state never authorizes generation or cleanup.
5. Local and provider-side ownership collisions fail without adoption.
6. Registrations have one shared owner per required provider scope.
7. Only complete deployment destruction permits local key removal.
8. Build and dry-run are deterministic and never access SSH files.
9. Connection results contain references, never private key material.
10. Repeated delete succeeds after completed cleanup.
