# SSH config standard for package skills

Status: normative target, revised 2026-09-09. Packages retain ownership of the
local SSH config play. Connection data comes from `colors-compute` node
results or the Colors cluster join. Existing package copies require migration
where they differ from this contract.

Consumers: packages that create hosts the operator can reach over SSH.
Key ownership is specified in [ssh-keypair.md](ssh-keypair.md).

## 1. Scope

A package MUST manage an SSH config block for an operator-reachable deployment,
in keygen and opt-out modes. It MUST NOT create an alias that cannot connect.
Packages without machines have no SSH config requirement. A deployment that
exposes only an entry node may publish only its entry alias.

Individual compute node operations MUST NOT edit `~/.ssh/config`. The package
writes one deployment block after compute results have been collected and
validated. Single-host packages use their single normalized node result.

## 2. Alias and marker

The entry alias is the profile. A package MUST NOT introduce an unrelated
configuration setting for that alias. New cluster node aliases follow
compute-cluster.md §6, using stable node identities even for singleton roles.

One deployment owns one block, identified by its profile:

```yaml
marker: "# {mark} {{ host_alias }} ANSIBLE MANAGED BLOCK"
```

Here `host_alias` is the deployment profile, not the current node alias.
The block contains the entry stanza and any node stanzas. Profiles and derived
aliases MUST be unique on the workstation and validated before rendering.
Separate remote backends do not prevent local alias or key collisions.

## 3. Stanzas and connection data

```sshconfig
Host <alias>
    HostName <node-ip>
    User <node-user>
    Port 22
    IdentityFile ~/.ssh/<profile>
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ForwardAgent no
```

`IdentityFile` and `IdentitiesOnly` MUST appear only in keygen mode. Opt-out
mode leaves operator SSH identity selection to the operator's configuration;
Ansible may separately use an explicitly supplied identity reference.

Each stanza MUST use its own node's returned address and user. Root MUST NOT
be hardcoded for clusters. The entry stanza uses the explicitly selected entry
node. Extra metadata MUST NOT be interpreted as arbitrary SSH directives.

The host-key policy MUST accept new hosts without accepting changed keys.
A package MAY use a deployment-owned `~/.ssh/<profile>.known_hosts` file with
explicit key pinning. It MUST then emit `UserKnownHostsFile` and MUST NOT
weaken host-key checks. `ForwardAgent no` MUST remain explicit.

The current machine contract uses port 22 and public addresses. Other routes,
such as a jump host, need explicit connection configuration and validation;
an unreachable private node MUST NOT receive a public-SSH stanza by assumption.

## 4. Lifecycle

A dedicated package-owned `ansible-local` stage manages the block against
localhost with `connection: local`. No parallel node branch writes the file.

Create writes or updates the block after all required compute and network
steps and the successful node join, before application convergence. A failed
join MUST NOT replace the existing block with a partial inventory.

Delete removes the block after any application cleanup that needs it and
before compute destruction. The keypair is removed only after every dependent
compute resource has been destroyed, as ssh-keypair.md requires. These are
different lifecycle points and MUST remain so.

Other verbs MUST NOT modify the block. Updating a dependency alone MUST NOT
edit local SSH configuration; a real lifecycle operation performs the edit.
Concurrent edits from different deployments MUST be serialized around the
read and write of the shared config file, without losing unrelated blocks.

## 5. Ownership and placement

On real create, before rendering or editing the block, the package MUST:

- Refuse any matching alias outside its owned markers. The diagnostic names
  the file and line and leaves the operator's stanza unchanged.
- Check every cluster alias against the deployment marker, not a marker made
  from each individual alias.
- Refuse leading global options before the first `Host` or `Match` stanza
  when inserting the managed block would change their scope.

The managed block MUST be inserted at the beginning of the file with
`insertbefore: BOF`, or an equivalent atomic insertion at byte zero while
holding the shared-file lock. This gives its connection settings precedence
over later wildcard settings. A regex targeting an arbitrary Host line is not sufficient.

For a leading-global-option refusal, the recovery is to place those settings
in an explicit `Host *` stanza in the intended position, usually at the end.
The package MUST NOT silently move them or insert a block that makes global
settings apply only to its final host stanza.

Preflight and the play MUST resolve the same file, using `$HOME` first and
runtime home only as fallback. They MUST validate aliases and connection
values against newline or directive injection before editing.

## 6. Build determinism

Build and dry-run MUST NOT read, create, modify, or require `~/.ssh/config`.
Runtime address, user, alias list, identity reference, and block state MUST
arrive as Ansible extra-vars. They MUST NOT be embedded into generated local
plays from real state. Keygen mode may determine whether identity directives
appear because it is known from desired state.

Goldens MUST contain neither workstation-specific SSH paths nor observed
node addresses in the local play. Different provider login users MUST not
require different copies of the play.

## 7. Package-owned play

Each package MUST own its local SSH config play. The play consumes the common
node/alias data contract and contains no provider-specific behavior. The
library supplies connection data and reusable validation, not an automatic
node-level write to the operator's shared file.

Provider additions MUST NOT require edits to this play. New connection data
that changes its contract requires an explicit versioned integration change.
Packages remain responsible for reviewing changes to SSH directives and
host-key policy.

`workspace/scripts/package-copies.py` checks existing copy families. Any
implementation migration changing those families MUST update its declared
variants and checks in the same change. Revising this standard alone does not
claim the existing copies or that script already implement the new contract.

## 8. Migration

A marker change requires explicit migration. The local play MUST remove the
old owned block before writing the replacement. Ownership checks MUST recognize
both old and new markers during the migration window. The old-marker removal
and recognition MUST retire together, only after affected deployment upgrades
have been accounted for; an upstream pin cycle alone is not proof of upgrade.

Alias changes, including old singleton aliases gaining a stable index, require
an explicit compatibility or replacement plan. They MUST NOT leave stale
stanzas or silently repoint an operator's alias to another node. Existing
provider-independent aliases may remain through a migration mapping.

Before migrating a copy, inventory its markers, aliases, key mode, home
resolution, and host-key policy. Preserve unrelated operator configuration.
Historical package-specific exceptions are migration work, not permanent
permission to hardcode root or write one block per node.

## 9. Conformance checklist

1. One package stage writes one block per SSH-reachable deployment.
2. The profile identifies the entry alias and ownership marker.
3. Node aliases use stable identities and each node's returned connection data.
4. Identity directives appear only in keygen mode.
5. Host-key checks remain strict about changed keys and agent forwarding is off.
6. Create follows the complete join; delete removes the block before compute.
7. Unowned aliases and unsafe leading options fail without file mutation.
8. Preflight and Ansible resolve the same file and serialize shared-file edits.
9. Build and dry-run never access the local SSH config.
10. The package-owned play contains no compute-provider branches.
11. Marker and alias migrations preserve ownership and unrelated stanzas.
12. Copy-family checks and package integration fixtures cover implementation changes.
