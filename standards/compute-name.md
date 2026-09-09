# Compute name standard for package skills

Status: normative target, revised 2026-09-09. Naming rules belong to
`colors-compute` in Green, Red, and Blue. Existing names require migration
mapping where they differ; this document does not authorize resource renames.

Consumers: every package skill that creates a named compute machine.

## 1. Deployment identity and defaults

A single-host deployment MUST use its profile as the default compute name.
A package MUST NOT require a separate name setting when the profile provides
that name. The profile also identifies the deployment SSH alias and keypair.

Profile identity MUST remain stable across lifecycle runs. Different backend
buckets do not make the same profile safe to reuse on one workstation because
SSH keys and aliases still share a namespace. Profiles MUST be validated for
safe use in local paths and aliases; they MUST NOT contain path traversal,
whitespace, or SSH configuration control characters.

Display names are not ownership identifiers. State keys and node identities
MUST NOT change when a display-name override changes. Backend or deployment
identity changes require explicit migration under compute-provider.md.

## 2. Optional name override

The library MAY accept provider-scoped display-name overrides such as
`digitalocean-name` or `vultr-name`. Absent, blank, or `REPLACE_ME` uses the
profile. A supplied value MUST pass the selected provider's naming rules.
This blank-value behavior applies to names, not to SSH key setting presence.

The library MUST resolve the effective deployment name once. Templates and
packages MUST NOT independently choose between profile and override.
Provider rules and configuration documentation belong to the library registry.

## 3. Derived names and node identity

Shared-resource labels derive from the resolved deployment name. New cluster
node display names derive from that name plus the stable `node_id` defined in
[compute-cluster.md](compute-cluster.md):

```text
single host:       <resolved-name>
homogeneous node:  <resolved-name>-<index>
named-role node:   <resolved-name>-<role>-<index>
```

Named-role nodes always retain their index, even when the role has one node.
Scaling from one node to several MUST NOT rename the existing node or its
state key. A node's identity MUST NOT depend on its position in a result list.

The library MUST validate final derived names against provider limits before
mutation. It MUST reject collisions and invalid names rather than silently
truncate them. Provider adapters may define deterministic resource-specific
label rules where resource types have different constraints; these rules MUST
be documented and tested in all colors.

The deployment keypair and provider-side key registration retain their
profile-based names under ssh-keypair.md. Display-name overrides MUST NOT
rename access credentials or SSH aliases.

## 4. Rename behavior

Changing a display name MUST NOT imply a guest-hostname repair or state move.
Provider adapters MUST document whether each name attribute updates in place,
requires replacement, or only influences creation-time guest configuration.
The library MUST NOT promise uniform rename behavior across providers.

A rename that requires replacement MUST follow an explicit rebuild or migration
procedure. Existing protection against unintended destruction remains in force.
A dependency update MUST NOT silently turn a label update into replacement by
selecting a different provider attribute.

Results MUST report the provider's observed name. Downstream steps MUST NOT
recompute an existing machine's name from newly edited desired state.

## 5. No required package constant

A package MUST NOT require a desired-state `package` key whose only allowed
value is the package's own name. Package identity belongs to the implementation;
deployment identity belongs to the profile.

## 6. Migration and evidence

Existing singleton role names, one-based indices, and package-specific suffixes
MUST be inventoried before adopting the new convention. Preserve their names,
node identities, state addresses, and aliases through explicit migration
mappings, or perform a separately authorized rename or rebuild.

Library parity checks MUST cover defaults, overrides, provider validation,
derived-name collisions, and stable names when counts change. Package checks
cover their topology-to-node mapping. Adoption is not permission to rename
existing resources merely to make a new golden match.
