# Compute cluster standard for package skills

Status: normative target, revised 2026-09-09. This revision replaces ONCE's
cluster-specific provisioning contract with Colors orchestration over
`colors-compute`. Existing packages require migration; this document does not
claim adoption is complete.

Consumers: every package that creates multiple compute machines. A single
machine with a private network uses the same library network contract without
needing a cluster-specific compute implementation.

## 1. Scope and execution model

A cluster topology is data expanded by a Colors fan-out. Each branch MUST
invoke the same `colors-compute` node operation used by single-host packages.
A cluster MUST NOT be implemented by a package-owned multi-machine OpenTofu
template, a resource count standing in for Colors fan-out, or a separate
provider-specific cluster provisioning API.

The library owns machine and shared-resource operations in all three colors.
Packages own topology, application roles, and downstream application work.
Provider and backend rules come from [compute-provider.md](compute-provider.md).
SSH lifecycle and aliases come from [ssh-keypair.md](ssh-keypair.md) and
[ssh-config.md](ssh-config.md).

The create flow is:

```text
validate topology and read recorded deployment state
prepare deployment key and shared provider resources once
fan out node requests through the common compute operation
join and validate every node result
write one deployment SSH config block
run downstream application steps
```

Dependent network attachments and peer rules MUST have explicit library-owned
steps if their inputs become available only after nodes exist. The join MUST
not report the deployment ready for Ansible until required network steps have
succeeded.

## 2. Topology and stable identity

A package MUST declare roles, effective counts, and an entry node as data.
Roles may be named, or null for a homogeneous topology. Counts MUST be positive
integers. Named roles MUST be unique and match `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`.
A null role MUST be the only role. An entry MUST resolve to exactly one node.

Expansion MUST produce one request per node, with:

```text
{node_id, role, index, compute configuration, shared-resource references}
```

`index` is non-negative and zero-based within its role. New homogeneous
clusters use the index as `node_id`; named roles use `<role>-<index>`.
Role declarations MUST reject collisions among generated identities and
aliases. `node_id` is stable through scaling and MUST NOT derive from branch
completion order, IP address, display name, or a singleton naming shortcut.
Role order followed by index defines the order of collected nodes.

Topology expansion MUST validate generated names, aliases, addresses used by
fixtures, and entry selection before mutation. Provider naming rules belong
to the library. Application-specific restrictions such as a fixed quorum size
remain package checks.

All branches MUST receive immutable or isolated inputs. No branch may change
the shared key, registry, backend configuration, or another branch's inputs.
This revision uses one selected compute provider per deployment; mixed-provider
clusters require a separately specified networking and ownership contract.

## 3. Join result and failure behavior

Each node returns the normalized result from compute-provider.md §4. The join
MUST collect all results, preserving useful non-secret metadata and connection
fields, and expose:

```text
{provider, entry_node_id,
 nodes: [{node_id, provider, role, index, name, ip, vpc_ip?, user, sudoer,
          uid?, ssh_key_id?, ssh_identity_file?, metadata?}],
 shared: {network references, key registration references, other metadata}}
```

The join MUST retain `provider` on each node as supplied by the library and
validate that it agrees with the deployment selection. It MUST preserve all
other non-secret fields returned by the node operation as well.

The join MUST refuse missing, duplicate, undeclared, or incomplete nodes.
Non-blank `name`, `ip`, `user`, and `sudoer` are required. `vpc_ip` is required
when the network contract provides private connectivity. It MUST verify node
identity against the request, not infer it from array position. Results MUST
be ordered by topology, not completion time. Packages validate any additional
metadata their application needs before running downstream steps.

A failed branch MUST fail the deployment and prevent application convergence.
Successful node states MUST remain available for retry or explicit cleanup;
the workflow MUST NOT discard them or automatically destroy healthy nodes.
The SDK may skip the join on failure, but the run must still report failed
node identities and preserve the record of attempted node states.

The join MUST NOT merge top-level `ip`, `user`, or key fields from one branch
over another. Downstream Ansible inventory and SSH configuration MUST consume
the node list and explicit entry selection. A real result never substitutes
build placeholders for missing nodes.

## 4. Shared resources, remote state, and deletion

The library MUST prepare shared resources once before node fan-out. Created
networks, shared firewall groups where applicable, provider-side key
registrations, and deployment-wide resource identifiers MUST have one recorded
owner. Node states only own node-specific resources and reference shared ones.

Network modes are:

- `created`: the library owns a network with a validated canonical CIDR.
- `discovered`: the library resolves an existing network using documented
  provider selection rules and never destroys it.
- `none`: no private-network attachment; no private address is required.

Network needs do not depend on node count. Source rules MUST use stable peer
identities or network references. Count changes MUST NOT reindex unrelated
firewall rules. Packages MUST declare their east-west trust boundary; using
an account-wide default network MUST be documented when it also trusts hosts
outside the deployment. Unsupported isolation requirements MUST fail before
mutation.

R2 and S3 state behavior follows compute-provider.md §6. Each node has its own
stable state key; shared resources have a separate state. The deployment MUST
persist a node ownership record, including attempted node identities and
state keys, before dispatching new branches. The record contains no secrets
and MUST survive partial creation and interrupted runs. Current desired state
alone is insufficient to discover resources that need cleanup.

Competing lifecycle runs for a deployment MUST be serialized. A deployment
lock or equivalent enforced coordination MUST cover shared-resource changes,
node ownership records, fan-out, and final cleanup. Independent node operations
within that run may execute concurrently. Per-state backend locks remain
required and are not a substitute for deployment coordination.

Retries MUST reuse recorded identities and state keys. Scaling down MUST
compare desired nodes against the ownership record and explicitly plan removal
of retired nodes. Removing a node from desired state MUST NOT orphan its state
or make a later delete forget it. Application teardown and quorum requirements
must run before retiring nodes when the package requires them.

Delete MUST address the recorded deployment, including partially created or
retired nodes, rather than requiring every node in current desired state to
exist. Unreadable recorded state blocks destructive work. Confirmed absent
node state is an idempotent cleanup case, not a fabricated node result.

After application cleanup, remove the deployment SSH config block, destroy
recorded nodes, and then destroy shared resources after their dependents are
gone. Remove the local keypair last, only after all compute and owned key
registration destruction succeeds. A failure retains ownership records and
the key for retry. An incomplete cluster may be deleted even though it cannot
pass the create join; teardown must not require a successful create first.

The ownership record MUST remain readable until final local-key cleanup has
succeeded. Destroying shared resources MUST NOT erase the only record needed
to retry that cleanup. Only then may the deployment record be retired.

## 5. Names

Display names follow [compute-name.md](compute-name.md). New cluster node
names derive from the resolved deployment name plus stable `node_id`.
They MUST NOT change when a role changes from one node to several.

Provider-reported names MUST be preserved in results. Existing names and
resource identities require an explicit migration mapping; adoption MUST NOT
silently recompute them using the new convention.

## 6. Aliases

A deployment writes one SSH config block marked with the profile. The bare
`<profile>` alias addresses the entry node. New clusters use
`<profile>-<node_id>` for each node alias, even for roles with one node.
Aliases MUST remain stable across scaling and unique within the block.

The collector MUST supply each alias with its node's address, SSH user, and
identity reference. Root MUST NOT be assumed. A node without a supported SSH
route MUST NOT receive a nonfunctional alias. Entry-only access is permitted
when the package intentionally exposes only that route.

The never-adopt check runs for every alias, using the deployment profile to
identify the owned block. Alias changes for existing deployments require the
marker and alias migration protections in ssh-config.md §8.

## 7. Fixtures and parity

Provider, keypair, and backend matrices belong to `colors-compute`.
Cluster contract checks MUST cover homogeneous and role-based topologies,
out-of-order completion, missing and duplicate results, extension preservation,
provider-appropriate users, and stable identities through scaling.

Lifecycle checks MUST cover partial creation, retry, scale-down, unreadable
state, delete after partial creation, shared-resource ownership, and repeated
delete. Builds MUST use deterministic documentation addresses and never read
remote state or local SSH files. Fallback generation MUST reject address
collisions or exhausted fixture subnets rather than emit invalid inventories.

Packages retain topology and application-inventory integration checks, failure
propagation, and lifecycle ordering. They do not duplicate the provider matrix.

## 8. Migration

Old cluster-wide states MUST NOT be treated as node states. Splitting one
state into shared and per-node states requires the migration procedure in
compute-provider.md §8, including backups, explicit ownership mappings,
recovery steps, and plan verification. No resource may remain managed by both
old and new states.

Legacy output translations, such as parallel IP lists or `hosts` renamed to
`nodes`, belong at this boundary. They MUST reject inconsistent lists rather
than guess identities. Existing aliases, key registrations, private networks,
and names MUST be accounted for before migration is declared complete.

The previous revision's package-specific adoption notes describe earlier
migrations. They do not exempt AutoMQ, the database clusters, Kubernetes
machine packages, ClickHouse, or any other machine-creating package from this
contract. Implementation status must be recorded separately from the standard.

## 9. Conformance checklist

1. Colors expands topology and calls the common library node operation.
2. Stable node identities determine distinct state keys and ordered results.
3. Shared resources and the deployment key are prepared once.
4. The join preserves every complete node result and rejects partial success.
5. Ansible and SSH config consume collected connection details.
6. Ownership records survive failures and enumerate cleanup targets.
7. Deployment coordination and backend state locks protect ownership.
8. Scale-down and delete retain keys until every dependent resource is gone.
9. Provider evidence is centralized; package application wiring remains tested.
10. Existing deployments migrate state explicitly without duplicate ownership.
