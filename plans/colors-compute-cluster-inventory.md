# Colors compute cluster migration inventory

Assessed 2026-09-09 from package source, package CLAUDE.md files, and the five revised workspace standards. This is a source inventory, not a live-state inventory. No credentials, generated deployment directories, or live state were read. Existing remote resources must be inventoried before migration.

## Scope and order

There are eight packages creating multi-host SSH machine clusters, all implemented in Green, Red, and Blue. Migrate these before single-host consumers. A dependency change alone cannot migrate existing cluster-wide state into the new library layout.

| Order | Package | Current compute and topology | Shared resources and constraints | Migration work |
|---|---|---|---|---|
| 1 | `automq` | Vultr; homogeneous `automq-node-count`, default three; `vultr_instance.node[count]` | Owned VPC, SSH registration, cluster firewall; public SSH and Kafka, private controller/internal ports | First homogeneous fan-out consumer. Split infrastructure state into shared and per-node states. Preserve broker IDs, names, SANs, quorum membership, bucket ownership and format records. Collect all node outputs before DNS, SSH config and Ansible. |
| 2 | `postgres-ha` | DigitalOcean; three homogeneous droplets, `digitalocean_droplet.node[count]` | Discovered regional default VPC; SSH registration and cluster firewall; existing trust includes other machines in that VPC | Prove discovered-network support without adopting/deleting the VPC. Preserve ordinal/address mapping, Patroni identity and etcd membership. Keep cleanup and backup safeguards. |
| 3 | `postgres-agy` | DigitalOcean; same three-node structural shape | Discovered VPC, SSH registration and firewall | Reuse the validated PostgreSQL integration while preserving package-specific application checks and resource mappings. |
| 4 | `mysql-ha` | DigitalOcean; three homogeneous droplets | Discovered default VPC, SSH registration, firewall, reserved-IP endpoint | Add explicit library capability for reserved IP ownership/attachment. Preserve endpoint identity and movement semantics, node ordinal mapping, MySQL member identity and backup restore behavior. |
| 5 | `mysql-agy` | DigitalOcean; same three-node structural shape | Same resource classes as mysql-ha | Port the validated topology integration; retain application-specific replication and restore checks. |
| 6 | `k8s` | DigitalOcean; `control-plane` and `worker`, currently one each, separate counted resource families | Owned VPC; role-specific firewalls and SSH registration | First role-based fan-out. Keep public API/SSH restrictions and pod/service CIDRs. Preserve old ordinal-based names through mapping. Cleanup must withdraw external-dns records and remove Kubernetes-managed load balancers before destroying nodes/VPC. |
| 7 | `langfuse` | Vultr; neon 1, redis 1, clickhouse 3, app 1; app is entry | Owned VPC, one key registration, four firewall groups; peer-specific `/32` rules become available after nodes | Implement library-owned post-node peer-rule stage before completed join. Preserve singleton resource names/aliases, ClickHouse count indices, Neon integration and existing resource-address manifests. Migration must not regenerate data/credentials. |
| 8 | `clickhouse` | hcloud; three ClickHouse/Keeper nodes and one Metabase host, already separate Colors branches and states | Owned network/subnet, separate access registration, per-node network attachment, post-node firewall, DNS-only WireGuard records | Replace ONCE template reuse with library calls and replace pass-through convergence with validated collection. Preserve existing stage state keys through mapping. Review old local/generated SSH identity and WireGuard ownership; do not silently adopt new profile-key conventions. |

Orders 2–5 may be implemented as a coordinated family once the AutoMQ contract is proven. ClickHouse is useful as a fan-out reference immediately, but its access-key migration makes it a poor first live migration. No single-host package should be migrated ahead of these machine-cluster integrations.

## Evidence and resource addresses

Canonical sources are under each package's `green/src/clj/io/github/getcolors/` and `green/src/resources/io/github/getcolors/`; Red and Blue carry behavioral equivalents.

- AutoMQ: `automq/cluster.clj`, `automq/workflow.clj`, and `automq/tools/infrastructure/main.tf`. Shared addresses include `vultr_ssh_key.machine`, `vultr_vpc.cluster`, `vultr_firewall_group.cluster`; nodes use `vultr_instance.node[index]`.
- PostgreSQL: `postgres_ha/validate.clj`, `postgres_agy/validate.clj`; resource directories use hyphens (`postgres-ha`, `postgres-agy`). Shared `digitalocean_ssh_key.machine` and `digitalocean_firewall.cluster`; node addresses are `digitalocean_droplet.node[index]`. Legacy readers translate parallel public/private IP lists and must reject length disagreement.
- MySQL: `mysql_ha/validate.clj`, `mysql_agy/validate.clj`; resource directories use underscores. Shared `digitalocean_ssh_key.machine`, `digitalocean_firewall.cluster`, and `digitalocean_reserved_ip.endpoint`; node addresses are `digitalocean_droplet.node[index]`.
- K8s: `k8s/validate.clj`, `k8s/workflow.clj`, `k8s/tools/infrastructure/main.tf`. Owned `digitalocean_vpc.cluster`, role firewall resources and counted control-plane/worker droplet families. Existing legacy adapter translates scalar control plane plus worker lists.
- Langfuse: `langfuse/topology.clj` and infrastructure template. `vultr_instance.neon`, `.redis`, `.app`, and `.clickhouse[index]`; shared `vultr_vpc.langfuse`, `vultr_ssh_key.machine`, role firewalls and peer rules. `test/resources/resource-addresses-{keygen,optout}.txt` are explicit address guards and must change only with reviewed mappings. Legacy hosts use null singleton indices.
- ClickHouse: `clickhouse/workflow.clj`, `clickhouse/tools.clj`, and `tools/tofu/{access,network,server,firewall}/`. Existing workflow branches `node-1`, `node-2`, `node-3`, `metabase`; shared network/access and later firewall stages. Server machine template comes from pinned ONCE hcloud resources; attachment is package-owned `hcloud_server_network.node`.

## Library capabilities required before package migration

The shared library must implement the same single-node operation in all colors, rather than wrapping an unchanged package multi-node template. All packages must stop enumerating compute providers and consume library validation and credentials.

Required capabilities include owned and discovered private networks, reusable deployment key registrations, isolated node inputs, role-specific sizes and firewall requirements, delayed peer rules, and normalized per-node SSH connection results. The join must validate declared identity, completeness, uniqueness and deterministic ordering and preserve non-secret downstream metadata. Source restrictions must remain at the provider layer as well as application-owned guest firewall rules.

R2 and S3 backends require one cross-color state-key derivation, shared state and durable attempted/retired node records. State keys cannot depend on display names, provider selection or current cluster size. Reads must distinguish absence from failure. A deployment lock must span multi-state operations; a lock on each tofu state alone is insufficient.

## State migration procedure

For each existing deployment, before any apply:

1. Record backend identity, old keys, resource addresses/IDs, access-key ownership, machine names, node identities and aliases. Back up state securely; do not commit raw state.
2. Produce an explicit old-address/old-key to new-address/new-key mapping for every owned resource. Discovered network data must remain discovered. Map old names and singleton aliases without implicit renaming.
3. Check ownership and freeze competing lifecycle operations. Transfer state using a reviewed procedure that cannot leave two active owners. Verify every resource exists in precisely one destination.
4. Run plans against the mapped state and require no unintended replacement, deletion, new key registration or new machine. A new empty state is not a migration success.
5. Verify interrupted-run recovery, repeated create/delete behavior and restore of prior ownership before a live upgrade. Never erase the sole deployment ownership record before final key cleanup succeeds.

The existing seven monolithic infrastructure states cannot be passed directly to a single-node reader. ClickHouse already has multiple keys, but adopting a new layout still requires explicit preservation or migration. Existing `local` backend fixtures may remain deterministic test inputs; production local-state deployments need remote backend migration.

## Dependencies and release sequence

Each package has `green/deps.edn`, `red/package.json`, and `blue/pyproject.toml`; launcher payloads under `skills/package-<name>-<color>/` may also contain dependency pins and runtime override metadata. Current consumers use ONCE cluster/SSH helpers; ClickHouse also resolves its hcloud template. Add matching `colors-compute` dependencies and remove compute-specific ONCE imports only after the replacement contract works.

Run package `bb test`, Red tests/typecheck, Blue tests, golden checks, `scripts/parity.sh`, and `scripts/launcher.sh`. Run `workspace/scripts/package-copies.py` after SSH module/play changes and update deliberate variant declarations with the implementation. Test that package configurations and Ansible accept a provider supplied by a library dependency bump without adding package provider branches.

Publish the library first, then real dependency pins in packages. Package instructions require pushed package commits before `bb pin` stamps launchers, followed by a second commit/push of stamps. Never invent a SHA. Deployment root launchers are copies and need refresh from installed payloads; preserve the distinction between lockfile installs and historic manual copies.

## Managed Kubernetes scope to resolve explicitly

`agent-network-k8s` provisions Vultr Kubernetes Engine and `agent-network-doks` provisions DigitalOcean Kubernetes, with managed node pools, registries, generated kubeconfig, and Kubernetes-owned load balancers/volumes. They have no SSH or Ansible host contract. They are compute-creating package skills, but the revised single-machine contract cannot express their existing behavior.

Do not declare universal package coverage while silently excluding them, and do not convert them to self-managed nodes as an incidental migration. Either add an explicit managed-cluster capability to the library with its own versioned operation, or record their migration as a separate unresolved requirement. Registry, pod-isolation, NetworkPolicy, Kubernetes cleanup and kubeconfig semantics must be preserved. This decision does not block the eight SSH-cluster implementations.

## Handoff

Inventory complete; no package sources or deployments changed. The next implementation task is the common library contract and AutoMQ integration. All live resource identity and migration claims remain unverified until the controlled state inventory is performed. Package CLAUDE.md descriptions of ONCE ownership describe current code and must be revised alongside migrations; revised workspace standards define the target contract.
