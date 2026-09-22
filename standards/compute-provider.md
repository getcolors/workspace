# Compute provider standard for package skills

Status: versioned normative contracts, revised 2026-09-22. `colors-compute`
v2 implements independent public-identity compute nodes, separate provider key
registrations, encrypted SSH resources, and scoped agent sessions. Alice is the
first integrated package. Other packages remain on their existing immutable
library pins; this is not an organization-wide rollout or state migration.

## Current v2 machine API

The library owns provider templates, validation, credential mappings, normalized
outputs, backend access and guarded single-resource lifecycle. The SDK/caller
owns topology, fan-out, joins, application ordering, and resource-scope cleanup.
No node call owns a shared SSH private key or an agent lifetime.

The exact contract lives in
[colors-compute/contracts/node.md](https://github.com/getcolors/colors-compute/blob/main/contracts/node.md).
Consumers MUST pin the matching color and refer to documentation at that pin.
A request supplies `node_id`, `state_filename`, absolute `workdir`, security and
network requirements, and an explicit public `ssh_resource` reference with key
and fingerprint. Where required, it also supplies the ready result of an
independently owned provider registration. The registry still owns provider
selection; package code MUST NOT recreate the provider matrix.

`node_plan` and build are credential-free. Real node operations are create,
inspect, and delete. There is no compute `prepare-access` operation and no
`ssh_identity_file` in node results. The package joins normalized machine data
with the scoped agent's socket/public-identity selection for SSH and Ansible.
See [ssh-keypair.md](ssh-keypair.md) and [ssh-config.md](ssh-config.md).

Each persistent root lives at `<workdir>/<profile>/<node_id>`. Local state is
`<workdir>/<profile>/<node_id>/<state_filename>`; remote state uses
`<s3-prefix>/<profile>/<state_filename>`. Local, S3, R2, OCI and GCS compute
backends are supported. Local storage is a real supported backend, not only a
test fixture. Provider registrations have distinct state files and
`registration-<name>` roots. Their state owns only the provider's public-key
object. Encrypted SSH authority has its own profile/name path and never enters
compute state or plans.

Compute identity pins profile, node, state filename, provider, SSH resource
reference and fingerprint. Existing root identity/backend changes MUST be
refused. Native backend locks protect state mutations; the caller serializes
operations sharing a local root. Create refuses deletion/replacement plans;
delete requires authorization and refuses create/update plans. Missing or
unreadable ownership cannot authorize deletion. A strictly empty readable state
can be inspected as destroyed. Compute and backend credentials are validated
before provider commands, with no secret embedded in generated templates.

The greenfield v2 API supplies no old-state compatibility or migration tooling.
Fresh v2 state MUST NOT be applied over resources owned by an older API. Existing
consumers keep their pinned contract and operational behavior until a separate
explicit integration/rebuild is authorized. A provider addition within the same
API remains a dependency update; a breaking ownership contract does not.

## Earlier contract for still-pinned consumers

The remaining 2026-09-09 sections record the preceding cross-package target.
Their deployment coordination, optional private-key path, keygen/opt-out matrix,
remote-only backend requirement and migration process are not requirements of
v2. Shared provider ownership, credential isolation, normalized results and
no-implicit-adoption principles remain applicable to both versions. Packages
that create no machines have no machine API requirement.

## 1. Scope and ownership

`colors-compute/` MUST provide Green, Red, and Blue implementations of one
contract. Each package implementation MUST depend on and pin the matching
library implementation in its dependency manifest and bundled launcher.
ONCE is a consumer, not the owner of shared compute behavior.

The library MUST own provider registration, validation, credential mappings,
provider templates, rendering, output normalization, state access, lifecycle
operations, and provider-specific SSH and network behavior. It MUST use the
matching Colors SDK for workflow and tool execution.

Packages own application configuration, application secrets, topology,
application checks, and downstream steps such as Ansible. They MUST express
compute requirements, including ports, protocols, source restrictions, and
network needs, as data accepted by the library. They MUST NOT maintain compute
provider allowlists, provider templates, or provider-specific compute branches.

A single-host package calls the node operation once. A cluster is a Colors
fan-out that calls the same operation once per node and joins the results,
as specified in [compute-cluster.md](compute-cluster.md). Shared deployment
resources have separate library operations with one owner, not one creator
per node.

## 2. Provider registry and configuration

The library MUST expose one authoritative registry in each color. The three
registries MUST agree on provider identifiers, configuration, credentials,
capabilities, and output behavior. Required settings and credential mappings
MUST derive from the selected registry entry, not parallel lists in consumers.

The compute providers in this revision are exactly:

| Provider | Required credentials |
|---|---|
| `azure` | No `COLORS_PAR_*` credential; OpenTofu uses the ambient Azure CLI session |
| `aws` | No `COLORS_PAR_*` credential; OpenTofu uses the ambient AWS credential chain |
| `google` | No `COLORS_PAR_*` credential; OpenTofu uses Application Default Credentials |
| `digitalocean` | `COLORS_PAR_DO_TOKEN` |
| `hcloud` | `COLORS_PAR_HCLOUD_TOKEN` |
| `vultr` | `COLORS_PAR_VULTR_API_KEY` |
| `yandex` | `COLORS_PAR_YANDEX_TOKEN` |
| `oci` | No `COLORS_PAR_*` credential; `oci-config-file-profile` selects a profile in `~/.oci/config` |

`no-infra` compute is unsupported in this revision. Selecting it MUST fail
validation, not select a fallback or create an implicit existing-host mode.
SMTP, DNS, and GitHub integrations are not compute providers in this library.

The registry MUST document each provider's non-secret settings, including
region or location, image, machine size, and network requirements. Existing
provider-scoped settings such as `vultr-plan` remain valid where the library
supports them. Settings belonging to unselected providers MUST be accepted
and ignored. Provider-specific validation runs only for the selected provider.

An unsupported selection MUST fail with `:provider-compute must be one of `
followed by the sorted registry identifiers. Missing credentials MUST name
only the required variable, never its value. Secrets MUST NOT enter desired
state, rendered templates, command-line arguments, or diagnostic output.

Packages MAY declare required capabilities through the common contract.
The library MUST reject unsupported requirements before mutation and explain
which capability is missing. It MUST NOT silently weaken network restrictions
or substitute a different machine configuration.

## 3. Templates and version-only provider adoption

Provider templates belong inside the library, separated by provider. A
provider is selected through the registry, not a conditional containing all
providers in one template. Provider-local optionals and SSH keygen branches
are allowed. Packages MUST NOT copy or override these templates.

The library MUST supply provider-independent inputs for application network
requirements and normalize provider outputs. A package MUST NOT need to
inspect provider names to render its application inventory.

After initial migration, adding a provider MUST require only a library
version or immutable dependency-pin bump in consumers, including their
lockfiles and launchers. It MUST NOT require package source, provider fixture,
or provider documentation edits. Users still supply the selected provider's
settings. This guarantee applies to a provider implementing the existing
contract and required capabilities; a contract change needs its own versioned
migration.

The library owns provider configuration documentation and provider coverage.
Package skill payloads MUST point to documentation for their pinned library
version and explain their own requirements. They MUST NOT duplicate an
exhaustive provider list that requires editing for every new provider.

## 4. Node result and lifecycle

Every successful node operation MUST expose one normalized `params` map:

```text
{node_id, provider, name, ip, user, sudoer,
 vpc_ip?, uid?, ssh_key_id?, ssh_identity_file?, metadata?}
```

`node_id` is a stable identifier supplied by the topology. It MUST NOT depend
on completion order, address, display name, or the current node count.
`provider` is the registry identifier. `name` is the provider's reported
resource name. `ip` is the public IPv4 address for the current machine
contract. `user` is the SSH login and `sudoer` is the account that can become
root. `vpc_ip` is required when the requested network provides private
connectivity. Additional addressing modes require an explicit contract
extension, not missing connection fields.

`ssh_key_id`, when present, identifies a provider registration owned by the
deployment's shared state; returning it does not transfer ownership to the
node state. `ssh_identity_file` is a local path reference, never key material.
`metadata` preserves useful non-secret provider outputs such as instance and
network identifiers. The library validates required provider metadata;
packages validate additional application requirements. Role and index are
topology data carried alongside these results by the join.

Every downstream stage MUST consume the normalized result or the cluster join
result, not raw provider outputs. A real converge MUST refuse missing or
incomplete results. It MUST NOT merge placeholder addresses under real outputs.

`build` and `--dry-run` MUST be credential-free and deterministic. They MUST
use documentation addresses in `192.0.2.0/24`, provider-appropriate login
values, and deterministic private-address fixtures where required. They MUST
NOT read remote state, ambient credentials, or local SSH files. A real run
MUST never substitute these fixtures for failed state reads or node outputs.

On real create and delete, the library MUST read existing state before
validating compute credentials. Backend credentials are validated first.
A recorded provider different from the requested provider MUST be refused
with `state holds a <recorded> machine; set provider-compute back to
<recorded> and delete first`. Provider switching remains a rebuild.
Legacy states without provider identity require an explicit migration mapping,
not a default guessed from the current registry order.

Compute destruction MUST remain protected by default through
`compute-prevent-destroy`. An explicit lifecycle override may authorize the
requested destruction, but MUST NOT bypass state ownership or provider-switch
checks. Migration MUST account for existing package-specific deletion guards
rather than silently removing them on dependency adoption.

State reads MUST distinguish confirmed absence, readable state, and failure.
Authentication failures, connectivity failures, malformed state, and an
uninitialized local backend MUST NOT count as absent remote state. The library
MUST initialize state access and establish absence or refuse the operation.
Unreadable state blocks both create and delete before resource mutation or
key generation. A fresh checkout is not evidence that remote state is absent.

## 5. Network contract

The library owns provider networks, attachments, and provider firewall rules.
Packages declare ingress requirements as protocols, ports, CIDR sources, and
stable peer or network references. Provider adapters translate those inputs.
The library MUST validate CIDRs and network requirements before mutation.

SSH sources MUST be non-empty for this public-SSH machine contract. Empty
optional service sources mean no ingress for that service, never open access.
Only declared inbound traffic is permitted; outbound traffic is open unless
the application requests a supported restriction. A guest firewall MUST NOT
substitute for the requested provider firewall.

A single machine may require a private network. Node count MUST NOT decide
whether a VPC is allowed. Created, discovered, and absent network modes are
specified in [compute-cluster.md](compute-cluster.md). Shared networks MUST
be prepared once and referenced by node operations. Provider requirements
and unavailable capabilities MUST be explicit in the registry.

## 6. Remote state backends

The library MUST own backend selection, configuration, initialization, state
reads, locking integration, and lifecycle access. `provider-backend` is
independent of `provider-compute`. Required remote backends are:

| Backend | Required credentials | Non-secret settings |
|---|---|---|
| `r2` | `COLORS_PAR_R2_ACCESS_KEY_ID`, `COLORS_PAR_R2_SECRET_ACCESS_KEY` | `r2-bucket`, `r2-endpoint` |
| `s3` | No `COLORS_PAR_*` credential; ambient AWS credential chain | `s3-bucket`, `s3-region` |

The library uses existing buckets; this contract does not create them.
Production lifecycle operations MUST use the selected remote backend. Local
rendering and isolated test backends do not constitute a third supported
production backend. Existing local-state deployments require explicit state
migration before adopting this contract.

Backend credentials MUST be isolated from compute credentials. In particular,
R2 credentials MUST NOT replace AWS compute's ambient credentials through a
shared `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` environment. Backend
configuration and caches containing credentials MUST remain private and MUST
NOT appear in committed artifacts or logs.

New deployments MUST use stable, distinct state keys for shared deployment
resources and each node, derived from deployment identity and node identity.
The provider and display name MUST NOT determine the key. The library MUST
publish one key derivation used by all three colors. It MUST preserve existing
keys until an explicit migration maps them to the new layout.

Backend locking MUST protect each state mutation. Per-state locks do not
serialize an entire multi-state deployment. Deployment orchestration MUST
serialize competing lifecycle runs as described in compute-cluster.md.
Changing bucket, endpoint, region, or state key MUST NOT silently select empty
state; it requires an explicit backend migration.

## 7. Evidence and parity

The library MUST own fixtures and golden renders covering all eight providers,
both keypair modes, and both remote backend configurations in all three colors.
Parity MUST compare normalized outputs, validation behavior, state-key
derivation, and rendered resources. Provider-specific login values and network
capabilities MUST be covered, not assumed to equal root or Vultr behavior.

Behavioral checks MUST cover confirmed missing versus unreadable state,
provider-switch refusal, incomplete results, credential isolation for AWS
compute with R2 state, and repeated delete after successful cleanup. Render
coverage MUST NOT be described as live cloud verification.

Packages retain integration checks for input delegation, application inventory,
error propagation, and lifecycle ordering. They MUST NOT duplicate the full
provider matrix. A version-only adoption check MUST add a test provider inside
the library and demonstrate that a single-host consumer and a cluster consumer
can use it with dependency changes alone.

## 8. Migration

This revision replaces the previous implementation ownership; it does not
mark existing packages conforming. Each migration MUST inventory templates,
resource addresses, backend keys, shared resources, SSH ownership, and legacy
outputs before changing dependencies.

Existing resource identities MUST survive migration unless an explicit rebuild
is authorized. Golden diffs alone cannot prove state safety. A migration MUST
provide the old-to-new state and resource mapping, state backups, an ordered
transfer procedure, recovery steps, and plan evidence that no unintended
replacement or duplicate ownership results. Never apply a new empty state
against resources still owned by an old state.

Splitting a cluster state into shared and node states is a state migration,
not an ordinary pin bump. Legacy output translators may exist at the migration
boundary; new application steps MUST consume the normalized contract.
Migrate one single-host and one cluster consumer as proof before broad rollout.
Historical package exceptions in the previous revision are migration evidence,
not permanent exemptions or proof that this contract has shipped.

## 9. Conformance checklist

1. Every compute-creating package pins its matching `colors-compute` library.
2. Provider code, registry, templates, credentials, and backends live there.
3. All eight compute providers and R2/S3 backends have parity evidence.
4. `no-infra` compute is refused.
5. Single-host and cluster node calls use the same operation.
6. Node outputs are complete, normalized, and free of secret material.
7. Unreadable state blocks mutation; provider and backend changes cannot
   silently redirect ownership.
8. Shared resources have one owner, and node states have stable identities.
9. New providers require dependency changes alone in migrated consumers.
10. Migration preserves resource ownership and includes reviewed plan evidence.
