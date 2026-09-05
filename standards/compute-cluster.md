# Compute Cluster Standard for Package Skills

Status: normative. The operations of §2 to §6 have one implementation:
ONCE's `compute-cluster` namespace (`io.github.getcolors.once.compute-cluster`,
`package-once-red`'s `computeCluster` export,
`package_once_blue.compute_cluster`), a sibling of the single-node `compute`
namespace that re-exports what is agnostic to the node count and adds what
is not. The single-node namespace is not modified by it.
ONCE commit 10e525a (the namespace landed in f8815a4 and shipped at
b1628b7; 31d3758 made `ssh/cleanup-step` fail the delete when a key file
survives, which every consumer below relies on since it adopted
`ssh-keypair.md`).
Reference consumer: `automq` (green, red, blue).
Consumers: `automq`, `mysql-agy`, `mysql-ha`, `postgres-agy`, `postgres-ha`,
`k8s`, `langfuse`.
Sibling of `compute-provider.md`, whose single-node contract this document
extends; everything the two share is cited there by section and never
restated here.

This document defines the multi-node contract `compute-provider.md` §1
defers: how a package declares the machines a deployment consists of, what
its compute stage hands to every later stage, how a private network is owned
or discovered, what the machines are called, and which `~/.ssh/config`
aliases reach them.

It exists because seven packages already answer these questions and no two
answer them the same way: `automq` and `langfuse` each hold a cluster module
with its own fallback nodes, partial-cluster refusal and alias derivation;
the MySQL and PostgreSQL pairs index parallel address lists by hand; `k8s`
reads a scalar and a list. Each is the same design written from scratch, and
a fix in one is invisible to the others.

## 1. Scope

This revision governs a package whose deployment is more than one machine,
binds a service to a private-network address, or builds east-west rules
between its own nodes. `automq`, `mysql-agy`, `mysql-ha`, `postgres-agy`,
`postgres-ha`, `k8s` and `langfuse` adopt it in this revision (§8).
`clickhouse` and `k3s` are deferred, for different reasons. `clickhouse`
hand-lists four servers with static private addresses across five OpenTofu
stacks, generates its key by shelling out to `ssh-keygen`, has no ssh-config
stage, and carries its isolation on a WireGuard overlay rather than the
provider firewall: it would be rewritten, not adopted. `k3s` provisions one
machine and belongs to the single-node backlog beside `walter`, `airflow` and
`vaultwarden`. Both remain under the exclusion of `compute-provider.md` §1,
and nothing here is to be copied into them by analogy.

Everything shared with the single-node contract holds unchanged and is cited
by section: the registry and the spec value (`compute-provider.md` §2),
template selection by directory and the no-state-move rule (§3), the
`params` output, provider switching as a rebuild, the legacy rule and the
unreadable backend (§4), the provider firewall, the source keys and the
DigitalOcean VPC refusals (§5), the keys the sibling standards own (§6),
fixtures and goldens (§7), and documentation (§8). Where this document names
a rule, it is the multi-node addition to that section, never a replacement.

**One operator and one checkout per deployment is a precondition of this
standard.** The state read and the apply are not one transaction, the SDK has
no deployment-wide lock, and this document does not add one.

## 2. The spec

A package MUST hand ONCE's `compute-cluster` namespace one spec value: the
spec of `compute-provider.md` §2 plus three keys.

```clojure
{:registry compute-providers          ; entries as in compute, plus :network
 :default  "vultr"
 :sources  {:non-empty ["ssh-sources"] :may-be-empty ["kafka-sources"]}
 :roles    [{:role nil :count-key :automq-node-count :count 3}]
 :entry    {:role nil :index 0}        ; optional; default = first node
 :fallback-subnet "10.110.0.0/20"}     ; optional; discovered networks only
```

- `:roles` is a vector, in play order. Each entry declares one role: `:role`
  is a string, or nil for a homogeneous cluster, in which case it is the
  only entry. `:count-key` names the desired-state integer that sets the
  role's node count; absent means the count is fixed. `:count` is the fixed
  count, or the default when the count key is absent from desired state. A
  present value is used as-is, and a present value that is not a positive
  integer is a validation error, never a default. `:fallback-offset`,
  optional, is the last-octet offset of the role's first fallback node; the
  default is 10 plus the number of nodes in the roles declared before it.
  The expected node set is data, not a package function, so that it is
  printable and parity-diffable.
- `:entry` is `{:role <role> :index <n>}`, both keys, naming the node the bare
  `<profile>` alias points to (§6). The default is the first node.
- `:fallback-subnet` is the private network a `build` uses for fallback
  `vpc_ip` addresses when the selected provider's network is discovered
  rather than owned. It exists for `build` alone.
- A registry entry's `:network` is `{:mode :created :key <cidr-key>}`,
  `{:mode :discovered}` or `{:mode :none}`; absent means `:none`. §4 defines
  what each mode implies.

`spec-errors` is static: it takes the spec alone, runs in every package's
spec-content test and at the head of `state-errors`, and its findings are
developer-facing and thrown, never returned to an operator. It refuses:

- an empty `:roles`;
- a role name that does not match `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, a
  duplicate role name, or a role equal to another role followed by
  `-<digits>` (`foo` beside `foo-0`), so that names and aliases cannot
  collide;
- a nil role that is not the only entry;
- an `:entry` that does not resolve to a declared role with a non-negative
  index, which is to say to exactly one declared node;
- a `:fallback-subnet` that is not a canonical IPv4 network, or one present
  when no advertised entry's network is `:discovered`.

`topology-errors` takes the spec and desired state and refuses:

- a present count key whose value is not a positive integer, with
  `:<count-key> must be a positive integer`;
- an `:entry` outside the effective count;
- a `:discovered` selected entry without a `:fallback-subnet`;
- a generated fallback address, public or private, that is not unique or
  lies outside its subnet's usable host range;
- a generated fallback name or alias that is not unique or exceeds 63
  characters, and a generated fallback name the selected provider's name
  rule rejects (compute's `:name-rules`, the same regex compute applies to
  the base name).

## 3. The `params` contract

The one representation of compute state is `params`. Every provider's
compute stage outputs one map, and every later stage reads only that map:

```text
{provider, ssh_key_id?, nodes: [{index, role?, name, ip, vpc_ip, user, sudoer, ...}], ...}
```

- `provider` and `ssh_key_id` are `compute-provider.md` §4's.
- `nodes` lists every machine. `index` is 0-based within its role. `role` is
  the declared role, or null for a homogeneous cluster. `name`, `ip`, `user`
  and `sudoer` are §4's per node; `vpc_ip` is the node's private address and
  is required whenever the selected network is not `:none`.
- ONCE interprets exactly `provider`, `ssh_key_id` and `nodes`, with the
  five named node fields. Every other key, at the top level or on a node, is
  an extension the package put there — `reserved_ip`, `vpc_id`,
  `vpc_ip_range`, a `droplet_id` on each node — and ONCE preserves it
  verbatim under `:once/cluster`. A parity case proves both.
- Extension keys are the package's to validate. After `adopt-state` and
  after `output-params` the package MUST run its own `params-errors` over the
  keys it added and refuse a real run with `compute state carries no <key>`;
  one wiring test per package proves it, and the legacy translation below
  applies the same checks.

A node id renders as `<index>` for the nil role and `<role>-<index>`
otherwise. Lists of ids follow declared role order, then index, joined by
`, `, and the wording of a message does not vary with the count.

**Fallbacks exist for `build` alone.** `build` and `--dry-run` render against
one fallback node per declared id: the public address is `192.0.2.0/24` plus
the role's offset plus the index; the private address is the network address
plus the same offset and index, computed with 32-bit arithmetic, taken from
the CIDR key on a `:created` network and from `:fallback-subnet` on a
`:discovered` one, and absent on `:none`; `user` and `sudoer` are `root`;
the name follows §5. On a real run there is no fallback substitution: a state
either describes the whole cluster or is refused.

`node-errors` is nil when `params` is nil, and otherwise reports, in this
order:

1. ids declared but not reported, with `the compute stage did not report
   nodes this package declares: <ids>` (a legacy `index: null` renders as
   `null` and is an undeclared id, which is why a package translates its
   legacy state before ONCE reads it);
2. ids reported but not declared, with `the compute stage reported nodes
   this package does not declare: <ids>`;
3. ids reported more than once, with `the compute stage reported <ids> more
   than once`;
4. ids whose entry lacks a non-blank string for any of `ip`, `name`, `user`,
   `sudoer`, or `vpc_ip` when the network is not `:none` — absent, `null`,
   `""`, whitespace and non-strings all count as missing — with `the compute
   stage did not report a complete node (ip, vpc_ip, name, user, sudoer) for
   <ids>; refusing to render a partial cluster`.

A present `params` with an empty `nodes` list reports every declared id
missing. The message strings are ONCE's contract and MUST NOT be reworded by
a consumer.

`resolved-cluster` refuses nil compute outputs on a real converge with
`compute produced no params output; refusing to converge against the
documentation addresses`, then runs `node-errors` over the outputs and fails
with its messages; only then does it merge `:once/cluster`. `adopt-state`
fails closed on an unreadable backend with `compute-provider.md` §4's
two-line message, refuses a `params` with any `node-errors`, and otherwise
adopts the machine key and merges `:once/cluster`; a readable state without
`params` leaves `:once/cluster` absent and the package decides what that
means for the event. A delete therefore addresses every node the state
describes and refuses a node without a complete entry.

**Legacy state.** A state whose `params` carries no `provider` is a
deployment created before the package adopted `compute-provider.md`, and §4
of that document refuses it on any provider but the default. A package whose
pre-adoption state recorded its nodes elsewhere translates them into
`params` in the reader it passes to `read-state`, so that `read-state` and
`adopt-state` need no second channel and a delete addresses every node the
deployment ever created. Three legacy shapes exist:

- `langfuse` recorded a `hosts` list whose singleton roles carry
  `index: null`; the reader renames `hosts` to `nodes` and a singleton's
  `index: null` to `0` before ONCE sees it. ONCE refuses `index: null` as an
  undeclared id.
- The MySQL and PostgreSQL pairs recorded parallel lists (`node_public_ips`,
  `node_private_ips`, and for MySQL `node_droplet_ids`); the reader zips
  them into nodes and refuses when the list lengths differ from each other
  or from the count key.
- `k8s` recorded a scalar control plane and worker lists; the reader builds
  node 0 of the control plane from the scalars and worker *i* from the lists,
  refused on unequal lengths.

The legacy outputs stay in the templates so that no state output disappears;
nothing reads them after adoption except that translation.

## 4. The network contract

The provider firewall of `compute-provider.md` §5 stands. The multi-node
addition is the private network the registry entry's `:network` selects:

- `:created` — the package owns a VPC on that provider, sized by the
  desired-state key the entry names. The key is required and MUST be a
  canonical IPv4 network — host bits zero, parsed as a real network, not the
  syntactic `cidr?` — refused with `:<key> must be a canonical IPv4 network
  such as 10.40.0.0/24`; every fallback offset MUST fall inside its usable
  host range. ONCE's `state-errors` filters the two DigitalOcean "must not
  create a VPC" messages out of compute's for a `:created` entry; compute
  itself is untouched.
- `:discovered` — the package uses the region's default VPC and refuses
  `<provider>-vpc-uuid` and `<provider>-vpc-cidr`, as `compute-provider.md`
  §5 already requires of DigitalOcean. On a real run the network CIDR is
  `params.vpc_ip_range`; `:fallback-subnet` stands in for it on a `build`.
- `:none` — no private network; nodes carry no `vpc_ip`.

The source of a package's east-west rules MUST be stated in its §8
documentation. A homogeneous cluster whose count is a desired-state key MUST
source east-west rules from the network CIDR or from stable per-node
identifiers the provider supports (DigitalOcean `source_droplet_ids`), never
from index-addressed per-peer /32 rules, because a count change would
reindex every peer rule. A fixed-count topology MAY use per-peer /32 rules.
A package on a **discovered** default VPC MUST state in its §8 documentation,
as a named security exception, that every machine in the account's regional
default VPC is inside its east-west trust boundary, and SHOULD prefer
droplet-id sources or an owned VPC when it next touches its firewall. None of
the seven packages changes a firewall rule in this adoption.

A source-list suffix beyond `ssh-sources` and `http-sources` — `kafka-sources`,
`client-sources`, `api-sources` — is carried by the spec's `:sources` map, by
name, as `compute-provider.md` §5 provides for; nothing here adds a second
mechanism.

## 5. Names

`compute-name.md` resolves one compute name for the deployment. The fallback
node names derive from it: `<compute-name>-<index>` for the nil role,
`<compute-name>-<role>` for a role of count one, and
`<compute-name>-<role>-<index>` otherwise. ONCE's `fallback-node-name`
implements the rule; compute's `name` supplies `<compute-name>`.

A template reports the name it gives: `params.nodes[].name` is read from
state, never recomputed. Adoption never renames: the rule governs fallbacks
and new packages only, and a machine keeps the name its template gave it. A
package whose legacy names differ from the rule — the DB pairs'
`<name>-node-<ordinal>` — overrides `:name` on the fallback nodes in its own
wrapper; ONCE never learns package naming.

## 6. Aliases

A multi-node deployment writes one `~/.ssh/config` block, marked with the
profile, containing one stanza per alias: `<profile>` first, then one alias
per node — `<profile>-<index>` for the nil role, `<profile>-<role>` for a
role of count one, `<profile>-<role>-<index>` otherwise. `<profile>` is the
`:entry` node. ONCE's `aliases` derives the list and `ssh-config-hosts`
supplies the local play's extra-vars, `[{:name profile :ip <entry ip>}
{:name alias :ip ip} …]`.

The never-adopt check of `ssh-config.md` §5 runs for every alias with a
two-arity `foreign-stanza-line`: the marker comes from the profile, the
stanza search takes the alias, and lines between the package's own markers
are skipped. A single-arity check that used each alias as its own marker
would read the package's own stanzas as foreign.

A package whose other nodes are reached through the entry node MAY write the
entry alias alone; `k8s` does.

## 7. Fixtures, goldens, parity

`compute-provider.md` §7 applies per advertised provider. The keypair-mode
axis applies to all seven consumers: `automq` and `langfuse` adopted
`ssh-keypair.md` at birth and the other five on 2026-09-05, so every
consumer renders two fixtures, `colors.yml` (keygen) and `optout.yml`
(opt-out), under each state backend. The opt-out golden is byte-for-byte
the package's pre-standard rendering under its own profile, which the
adoption proved by rendering the opt-out fixture, substituting the profile
and diffing against the old committed golden; the one permitted exception
is the `ansible-local` play where a `ssh-config.md` §8 marker migration ran
in the same change.

**Adoption changes only the enumerated paths and hunks.** Only code and
tests move. Every golden diff is empty except for the files and hunks §8
names per package, a byte outside that set is a behaviour change, and it
blocks the commit. The gate is `git diff --stat -- test/resources/golden`
listing only the named files and `git diff -- test/resources/golden` showing
only the named hunks, read before the commit.

`langfuse` additionally commits two configuration-address manifests, one per
keypair mode (`test/resources/resource-addresses-keygen.txt` and
`…-optout.txt`): every `resource "…" "…"` line and its `count` or `for_each`
line from the rendered `main.tf`, the opt-out one lacking
`vultr_ssh_key.machine` by design, that each rendered tree must reproduce
exactly. That proves the configuration's block addresses and their count
expressions, which is what a plan is computed from. It does not read the
live state and is not a `tofu state list` comparison.

## 8. Adoption

New packages are born conforming and born delegating to ONCE's
`compute-cluster` namespace; `create-package-skill` references this document.
Existing packages adopt behind their normal pin flow: the ONCE pin at or past
the commit above in every colour, the green SDK pin at `3f33f5d`; a
`compute-providers` registry with `:network`; a spec; delegation; one wiring
test per safety boundary and one spec-content test per colour; the test
`a-real-create-on-a-fresh-work-directory-reports-the-credentials-not-a-crash`;
the pure-function matrices ONCE now tests dropped. Two commits: the adoption
and `chore: pin the bundled launchers`.

### automq

Registry `{"vultr" {… :network {:mode :created :key :vultr-vpc-subnet}}}`;
roles `[{:role nil :count-key :automq-node-count :count 3}]`; sources
`{:non-empty ["ssh-sources"] :may-be-empty ["kafka-sources"]}`. `cluster.clj`
keeps broker names, quorum, listeners, principals and ACLs; `node-count`,
`indexes`, `fallback-nodes`, `nodes`, `missing-node-error`, `machine-name`
and `compute-name` delegate. `tools/state-output` becomes the reader passed
to ONCE's `read-state`; delete adopts through `adopt-state`, failing closed
where it proceeded on nil before. `ssh_config/aliases` and `ssh-config-hosts`
delegate. `launcher.sh` greps `resource "vultr_vpc"`.

Permitted golden change: the `provider = "vultr"` line in `params`, in both
goldens (`automq-fixture`, `automq-optout`). Nothing else.

### mysql-ha and mysql-agy

Registry `{"digitalocean" {… :network {:mode :discovered}}}`; roles
`[{:role nil :count-key :cluster-nodes :count 3 :fallback-offset 11}]`;
`:fallback-subnet "10.110.0.0/20"`; sources
`{:non-empty ["ssh-sources" "client-sources"]}`. `load-infrastructure-step`
becomes ONCE's `read-state` plus `adopt-state`. The reader returns `params`
when present and otherwise synthesises one from the legacy outputs:
`provider "digitalocean"`, `reserved_ip`, `vpc_id` and `vpc_ip_range` copied,
node *i* = `{index i, role null, name utils/node-name(i+1), ip
node_public_ips[i], vpc_ip node_private_ips[i], droplet_id
node_droplet_ids[i], user "root", sudoer "root"}`. It refuses with `legacy
state lists <n> public addresses, <m> private addresses and <k> droplet ids;
refusing to guess the cluster` when the three lengths differ or differ from
`cluster-nodes`, and with `legacy state carries no reserved_ip` when that is
absent. `params-errors` requires a non-blank `reserved_ip` and `vpc_id`, a
canonical `vpc_ip_range`, and a non-blank `droplet_id` on every node.
`tools/nodes` maps ONCE's nodes to the package's 1-based ordinals and
overrides fallback names with `utils/node-name` (`<name>-node-<ordinal>`),
so the rendered inventory is byte-identical. The package's own checks stay:
`cluster-nodes = 3`, `digitalocean-vpc-mode: default`; its CIDR messages are
replaced by ONCE's.

Permitted golden change, for each of the two packages: one `output "params"`
block (`provider`, `reserved_ip`, `vpc_id`, `vpc_ip_range`, `nodes` with
`droplet_id`) added to
`test/resources/golden/local/<pkg>-fixture/<pkg>-infrastructure/main.tf` and
the same block in `test/resources/golden/r2/<pkg>-fixture/<pkg>-infrastructure/main.tf`.
No other golden file.

Keypair and ssh-config adoption (2026-09-05, tri-colour, pin at or past
the commit above): `digitalocean-ssh-keys` leaves `:required` and its
absence is keygen mode; `digitalocean-ssh-private-key` is required in
opt-out mode only. The template declares `resource "digitalocean_ssh_key"
"machine"` named after the profile, references it by attribute in
`ssh_keys`, and records `ssh_key_id` in `params`, all under the
`ssh-keygen` conditional. The pair gains an `ssh` wrapper over ONCE's
namespace, the multi-node `ssh_config` module and the unified play (§6;
`ssh-config.md` "The copies are checked as one"), the block written after
the infrastructure stage and withdrawn before the destroy, and the keypair
removed last. Permitted golden change: the `digitalocean_ssh_key` resource,
the attribute reference and `ssh_key_id` in the keygen `main.tf`; the
`IdentityFile` pair in the keygen play and `ansible_ssh_private_key_file` on
every node of the keygen inventory; the new `ansible-local` stage in every
golden; and the new `<pkg>-optout` trees, byte-identical to the previous
`<pkg>-fixture` trees under the substituted profile apart from that stage.

### postgres-ha and postgres-agy

As the MySQL pair, with `:fallback-subnet "10.114.0.0/20"`; the explicit
`0.0.0.0/0` refusal stays package-owned. The legacy mapping is the MySQL
pair's without `droplet_id`, `reserved_ip` and their refusals: the two lists
must agree with each other and with `cluster-nodes`, and `vpc_id` and
`vpc_ip_range` must be present and non-blank, the CIDR canonical.
`params-errors` requires `vpc_id` and `vpc_ip_range`. The `ansible-local`
play's per-node loop takes ONCE's `ssh-config-hosts`, and its marker migrates
to the profile — the `ssh-config.md` §8 migration already owed — which
changes the rendered play.

Permitted golden change, for each of the two packages, three files per
variant (`local` and `r2`): the `params` block in `main.tf`; the
`ansible-local/main.yml` play rewritten to §6's shape (one block marked with
the profile, one stanza per alias, plus the `ssh-config.md` §8 one-cycle task
that removes the old package-prefixed per-node blocks); and the alias list in
`acceptance.sh`, which reaches the nodes through the aliases the block writes
and therefore follows them from `<name>-1..3` to `<profile>-0..2`. Nothing
else.

Keypair adoption (2026-09-05): as the MySQL pair's, with the `ssh_keys`
list rendered from an `:ssh-keys-hcl` value that is `[]` in keygen mode and
the quoted literal list in opt-out mode, the key resource declared before
the droplet, and the §8 one-cycle removal task retired (its cycle ran with
the cluster adoption above). Permitted golden change: the key resource, the
attribute reference and `ssh_key_id` in the keygen `main.tf`; the
`IdentityFile` pair in the keygen play and the key file in the keygen
inventory; the play's removal task gone in every golden; and the new
`<pkg>-optout` trees, byte-identical to the previous `<pkg>-fixture` trees
under the substituted profile apart from the local stage.

### k8s

Registry with `:network {:mode :created :key :digitalocean-vpc-cidr}`; roles
`[{:role "control-plane" :count-key :control-plane-count :count 1}
{:role "worker" :count-key :worker-count :count 1}]`; `:entry {:role
"control-plane" :index 0}`; sources `{:non-empty ["ssh-sources"
"api-sources"]}`. The reader translates the legacy outputs into `params`:
control-plane node 0 from `control_plane_public_ip` and
`control_plane_private_ip`, worker *i* from the two worker lists, refused on
unequal lengths, names from the package's own naming, `vpc_id` copied from
`digitalocean_vpc_id` and refused when absent or blank. `params-errors`
requires `vpc_id`. The block writes the entry alias alone (§6).

Permitted golden change, four files: the `params` block (`provider`,
`vpc_id`, `nodes` with roles `control-plane` and `worker`) in
`test/resources/golden/{local,r2}/k8s-fixture/k8s-infrastructure/main.tf`,
and the fallback public addresses `192.168.0.10` and `192.168.0.11` becoming
`192.0.2.10` and `192.0.2.11` in
`test/resources/golden/{local,r2}/k8s-fixture/k8s-ansible-remote/inventory.json`,
the only golden files that carry them. The private fallbacks `10.20.0.10`
and `10.20.0.11` are unchanged: offsets 10 and 11 in the
`digitalocean-vpc-cidr` network. Nothing else.

Keypair and ssh-config adoption (2026-09-05): `digitalocean-ssh-key-fingerprint`
becomes `digitalocean-ssh-keys` — the same value, an id or a fingerprint —
and the old name is refused by name (`ssh-keypair.md` §8). One
`digitalocean_ssh_key` for the cluster, referenced by attribute on both
droplets, `ssh_key_id` in `params`. The `ssh_config` module and the play are
the single-node copies (the block writes the entry alias alone, §6), with
the play's marker migrated from `# BEGIN k8s <alias>` to the alias alone
behind a `ssh-config.md` §8 one-cycle removal task, `User` taken as an
extra-var, and `insertbefore: BOF`; the inventory names the generated key
in keygen mode. Permitted golden change: the key resource, the two
attribute references and `ssh_key_id` in the keygen `main.tf`; the key
file on both nodes of the keygen inventory; the play in every golden; and
the new `k8s-optout` trees, byte-identical to the previous `k8s-fixture`
trees under the substituted profile apart from the play.

### langfuse

Registry `{"vultr" {… :network {:mode :created :key :vultr-vpc-subnet}}}`;
roles `[{:role "neon" :count 1 :fallback-offset 10} {:role "redis" :count 1
:fallback-offset 11} {:role "clickhouse" :count 3 :fallback-offset 20}
{:role "app" :count 1 :fallback-offset 12}]`; `:entry {:role "app" :index
0}`; `:clickhouse-nodes = 3` stays a package check; sources `{:non-empty
["ssh-sources"] :may-be-empty []}`, with `vultr-http-sources` left to the
package because it accepts the symbolic `cloudflare`. The reader translates a
state `hosts` key to `nodes` and a singleton's `index: null` to `0` before
ONCE sees it — the live deployment's recorded shape, and a test uses a
fixture copied from it. `golden.sh` gains the two configuration-address
manifests of §7. No live run: `langfuse-vultr` is live, its twenty tofu
resource addresses do not move, its next converge plans an output change
only, and the adoption commit message says so.

Permitted golden change: the `params` output renamed `hosts` to `nodes`,
singleton `index = 0`, and `provider = "vultr"`, together with the comment
directly above that output, in both goldens; every resource block
byte-identical. Nothing else.

## 9. Conformance checklist

A package conforms when:

1. It owns a `compute-providers` registry whose entries carry `:network`,
   agreeing across the three colours.
2. Its spec declares `:roles` as data, in play order, with a nil role alone
   when present, and an `:entry` that resolves to one declared node.
3. `spec-errors` passes in every colour's spec-content test, and
   `topology-errors` runs before any provider call.
4. Every provider outputs `params` with `provider`, `nodes` carrying the
   five node fields, a 0-based `index` per role and a null `role` for a
   homogeneous cluster, and `ssh_key_id` in keygen mode.
5. Its extension keys ride inside `params`, validated by its own
   `params-errors`, and no package code reads a legacy output except its
   reader's translation.
6. `build` and `--dry-run` render fallback nodes on `192.0.2.0/24` and the
   created CIDR or `:fallback-subnet`; a real run substitutes no fallback.
7. A real converge refuses nil outputs and a partial, undeclared or
   duplicated node with ONCE's messages, unreworded.
8. A real delete fails closed on an unreadable backend and refuses a node
   without a complete entry; a pre-adoption state is translated so that the
   delete addresses every node.
9. A `:created` network owns a VPC from a canonical CIDR key; a
   `:discovered` network refuses the VPC keys and names the default-VPC trust
   boundary as a security exception in its documentation.
10. The east-west rule source is stated in its documentation, and a
    count-key cluster never uses index-addressed per-peer /32 rules.
11. Fallback names follow §5, names are read from state, and adoption
    renames nothing.
12. One block, marked with the profile, holds one stanza per alias of §6,
    checked with the two-arity `foreign-stanza-line`.
13. One fixture and golden per advertised provider; adoption changes only
    the paths and hunks §8 enumerates.
14. It delegates to ONCE's `compute-cluster` rather than copying it; its own
    tests keep one wiring test per safety boundary, one spec-content test per
    colour, one `params-errors` test, and the fresh-work-directory create
    test.
