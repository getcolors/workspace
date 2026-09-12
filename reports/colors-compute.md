# Colors Compute Audit

Deep audit of `getcolors/colors-compute` at commit `4f36a7f` (main, 33 commits,
9–11 Sep 2026). Audited 11 Sep 2026. Scope: the committed HEAD only.
Shareable page: https://claude.ai/code/artifact/9fc08527-ab13-4a19-9cdb-7b8efbc51bca

## Review update, 12 Sep 2026

The audit below describes commit `4f36a7f`. A source review against that
commit confirmed the lifecycle dead ends and corrected two impact claims.
All three executors reject replacement plans before apply, even when
`compute-prevent-destroy` is false. Findings 6 and 7 therefore describe blocked
reconvergence and missing template protection, not demonstrated automatic
replacement through the library. The duplicate Red SDK remains a packaging
issue, but the claimed additional `StepError` exit-code regression needs a
reproduction because orchestration already maps node exceptions to exit code 1.
The original severity counts below have not been recalculated.

Commit `bd82520` fixed finding 2 in all three colours and added regression
tests. The source review used `58ac766` as the current checkout. The original
suite counts are historical evidence, not a new test run.

## Remediation, 12 Sep 2026

Implementation commit: [`2e55b05`](https://github.com/getcolors/colors-compute/commit/2e55b05c94da2835bd4914076ef0845140dab71f).

The library now handles deletion before key preparation and resumes retirement
after key removal. Prepared deployments can delete without local key files.
Cleanup still verifies any surviving key material against the journal
fingerprint. Shared fixtures cover the new retirement rules, and integration
tests cover partial keys, foreign files and deletion from a new machine.

Interrupted key phases still retain their locks. The new
[manual recovery procedure](https://github.com/getcolors/colors-compute/blob/2e55b05c94da2835bd4914076ef0845140dab71f/contracts/key-phase-recovery.md)
requires process termination, state and provider checks, and a conditional
journal repair with exact read-back verification. It covers held locks in
intent, cleanup and removed key phases. Findings 1 and 9 have code fixes;
finding 3 now has the documented recovery route requested by the audit.

Managed GCS operations now resolve the configured project's number through
Resource Manager and compare it with bucket metadata before mutations. This
addresses finding 4. Managed operations require `resourcemanager.projects.get`.
Object reads verify that the bucket exists before treating an object 404 as
absence, addressing finding 12. External readers therefore also need
`storage.buckets.get` for this check. The new
[GCS contract](https://github.com/getcolors/colors-compute/blob/2e55b05c94da2835bd4914076ef0845140dab71f/contracts/managed-gcs-backend.md)
documents these permissions and the ownership checks.

Both Red manifests now use an SDK peer dependency. The Red development SDK
pin is `e24217c`, and Green pins SDK `a918861`. Applications must keep an
explicit Red SDK Git pin. Existing consumer pins and deployment payloads have not been updated;
they receive these fixes only after adopting the new library commit.

Local verification passed 591 Blue tests, 362 Red tests plus typecheck, and
132 Green tests with 1,539 assertions. Shared parity passed 496 cases per colour.
Both Red installed-package layouts passed the isolated installation check and
resolved the consumer's SDK without a nested copy. A separate consumer install
using the pinned Git SDK also passed. The backend, journal, managed cleanup and
power HTTPS probes passed. Registry
and packaged-resource checks, migration tests, network and option checks also
passed. OpenTofu accepted the destroy-only public key in representative schema
checks for all eight providers. These were local checks with synthetic
credentials, not live cloud deployment tests.

## Verdict

Every offline check passes at HEAD, and the three colours agree on everything
the shared fixtures cover. The exposure is in what the fixtures do not reach.
The coordinator, executor, orchestrator, recovery, SSH and managed-bucket
modules are tested per colour only, and that is where this audit found three
lifecycle states the library can enter but never leave, one missing ownership
assertion on the new GCS backend, two provider templates without the guards
their siblings have, and a packaging fault that makes every Red consumer run
the library's fan-out on an SDK older than the one it pinned.

A concurrent Codex session began writing an OCI Object Storage backend into
this checkout at 15:17, three minutes into the audit. Every finding below was
verified against `git show HEAD:`, and that in-progress work is excluded.

| Severity | Count |
|---|---|
| High | 7 |
| Medium | 17 |
| Low | 22 |
| Checks passing | 36 / 36 |

## What was run

All checks from the README and the CI workflow, plus the three scripts under
`test/` that neither runs, executed locally on a clean checkout before the
working tree went dirty. Local OpenTofu is 1.11.5 where CI pins 1.12.5;
nothing observed depended on the difference.

| Suite | Result | Note |
|---|---|---|
| Green `bb test` | 113 tests, 1347 assertions | also passes against the newest Green SDK (a918861) |
| Red `bun test` + typecheck | 324 tests | also passes against the newest Red SDK (e24217c) |
| Blue `pytest` | 517 tests | |
| Shared parity | 479 cases per colour | pure reducers and renderers only |
| Registry, resource, recipe, option, power, controller, endpoint, execution scripts | 14 scripts pass | |
| Backend, backend HTTP, journal HTTPS, power HTTP, power OCI, managed probes | 6 probes pass | loopback only, synthetic credentials |
| Eight `providers/*/check.py` with tofu | 8 / 8 | |
| Migration planner, provider adoption, endpoint schema, ICMP schema | 4 / 4 | the last three are run by nothing in CI |
| GitHub Checks on main | **3 of the 6 commits today were red** | f75fea1, f9a6c78, 691d8c5 failed `registry.py`; the colours landed in separate pushes |
| Workspace `compute-copy-contracts.py` | **2 failures / 91 contracts** | once/blue and redis/red, see consumers |

## High

### 1. A delete before key preparation wedges the journal for good

`green compute_orchestration.clj:92,106` · `red orchestration.ts:65,84` ·
`blue orchestration.py:138,167` · reducer `lifecycle.py:220–238`

Delete commits `begin-delete` (status → `deleting`) and then unconditionally
requires the key phase to be `prepared`. The reducer has no path from
`deleting` back to `active`, and none from key `absent` to `removed`. So if a
create fails after `declare` but before `key-intent` (a refused validation, a
missing `ssh-keygen`, an unwritable home) and the operator runs delete to
clean up, the journal is left in a state where create refuses (status must be
`active`) and delete refuses (key must be `prepared`), forever. Red and Blue
contain a guard for exactly this case that is dead code because the stricter
check follows it. Green has no guard. The lifecycle contract defines no
transition that covers it.

### 2. A declared node with a retained empty state cannot be deleted; trying converts it to a permanent `failed` record

Resolved after the audited snapshot by `bd82520`.

`green compute_orchestration.clj:52,124` + `compute_execution.clj:78,98` ·
`red orchestration.ts:37,94` + `execution.ts:54,82` ·
`blue orchestration.py:76,191` + `execution.py:94,148`

For `declared` nodes the orchestrator short-circuits only when presence is
`absent`. An empty state envelope left by a previous generation's destroy is
explicitly allowed by the tofu-runtime contract, and with it present the
converge refuses empty documents before it reaches its own "already empty,
treat as destroyed" branch. The node becomes `failed/destroy`; on the next run
the failed phase demands readable state with `params.provider`, which an empty
state lacks. Scale down after a failed shared create and re-run create to hit it.

### 3. Any failure inside a key phase leaves the remote lock held with no library recovery path

Reducer release guard: `green compute_lifecycle.clj:112` · `red lifecycle.ts:132`
· `blue lifecycle.py:238` · `green compute_ssh.clj:153`

`release` refuses key phases `intent` and `cleanup`. A failure between
`key-intent` and `key-prepared`, or after `key-cleanup`, therefore leaves the
journal `held`; every later `acquire` returns `lifecycle lock held`, and
takeover is forbidden by the coordination contract. `compute_recovery` covers
only the AWS shared-create case. The manual procedure is documented nowhere in
the repository. This is fail-closed by design, but the triggers are mundane
and the operator is given no exit.

### 4. The managed GCS bucket has no owner assertion

`blue managed_gcs_backend.py:24,39–46` · `red managed-gcs-backend.ts:13,21–24`
· `green compute_managed_gcs_backend.clj:19,29–32` · compare
`blue managed_backend.py:52,56`

The S3 path derives the account from `sts get-caller-identity` and passes
`--expected-bucket-owner` on every call. The GCS path takes the project from
the configured `google-project` and checks only that three labels, the
location and a marker object under `_colors/` match. Those are set by whoever
can write bucket metadata, and `projectNumber` is never compared. GCS bucket
names are global and reusable the moment `finalize` deletes one, so a squatter
can pre-create the name after a delete, set the labels and marker, and receive
the next generation's OpenTofu state, provider secrets included. Live
exploitability was not tested; the code path was.

### 5. Every Red consumer runs the library's fan-out on a second, older copy of the Red SDK

`red/package.json:18` and root `package.json:9` declare `red` as a hard
dependency · `red/src/orchestration.ts:4` imports `run` from it · 22 consumer
`bun.lock` files carry a nested `colors-compute-red/red`

Because the library pins the SDK as a regular dependency rather than a peer,
bun installs `node_modules/colors-compute-red/node_modules/red` at db9bfe6
beside the consumer's own SDK. Verified physically in once, clickhouse and
langfuse. The library's `orchestrate` calls `run` from its nested copy, so the
SDK commit e24217c ("Fix nested joins, frozen inputs, and inventory values"),
which rewrote `joinForks` and join base options, reaches no consumer's cluster
join even where the consumer pinned it. Two module instances can break
`instanceof StepError` across a module boundary. This audit did not establish
an additional exit-code regression in orchestration, which already catches
node exceptions and returns exit code 1. The
library's own suite passes against e24217c, so the fix is to make `red` a
`peerDependency` and bump the dev pin. Green (tools.deps picks the top-level
pin) and Blue (`blue>=0.1.0` resolves to the consumer's source) do not have
this problem.

### 6. OCI image discovery re-resolves on every plan and nothing pins the result

`providers/oci/node-image-discovery.tf.json.template:3–16` ·
`node.tf.json.template:34,41–43` · resolver: `red provider-request.ts:182`,
`blue provider_request.py:297`, `green compute_request.clj:250`

Without `oci-image-id` the resolver selects the discovery stage on every
call, which picks the newest Canonical Ubuntu 24.04 image into `source_id`,
and the instance lifecycle has only `prevent_destroy`. The Yandex discovery
template guards the same field with `ignore_changes`. When Canonical publishes
a new image the next reconverge plans a replacement: with the guard on, the
deployment cannot reconverge and drift reports `error` until the operator pins
the existing image. With the guard lifted, the executor still rejects the
replacement plan before apply. Automatic VM recreation is not established
through the library. The OCI README says the
lifecycle must record and pin the resolved image; no colour does.

### 7. AWS shared network and key pair carry no `prevent_destroy`

`providers/aws/shared.tf.json.template:17–96` ·
`shared-keygen.tf.json.template:3–8` · also `oci/shared.tf.json.template:24–30`
(NSG)

VPC, subnet, internet gateway, route table and security group are unguarded;
only the node and the per-role security group are. Every other provider
guards its network and firewall, and DigitalOcean, hcloud and Vultr guard the
keygen resource. Editing a CIDR, availability zone or the public key on a live
AWS deployment plans replacement without the guard that stops the same edit
elsewhere. The OCI network security group is unguarded in the same way. The executor
independently rejects replacement plans before apply in all three colours.
These template omissions remove an extra protection for direct template use;
they do not demonstrate automatic replacement through orchestration.

## Medium

### 8. Committed parity bug in the backend-plan error text (Blue)

`blue rendering.py:40` says `r2, s3, gcs` · `red rendering.ts:26` and
`green compute.clj:141` say `gcs, r2, s3`

The fixtures only exercise `validate`, and Blue has no unknown-backend test
for `backend_plan` (Red and Green do). First divergence found in a shared
error string.

### 9. Delete requires the managed key files, though destroy never needs key material

`blue orchestration.py:166–170, ssh.py:144,182` · `red orchestration.ts:84,
ssh.ts:57,79` · `green compute_orchestration.clj:107, compute_ssh.clj:112`

Delete re-runs keypair preparation with a forced create event solely to
verify the key, and preparation refuses when either file is missing. A delete
that destroyed everything and unlinked the key but crashed before `retire`, or
an operator on a new machine, cannot delete. This is the library-side twin of
the workspace `fileexists` rule: the templates here render `{{public_key}}`
rather than reading a file, so the guard has to live in the delete path, and
it does not.

### 10. Caller extras can override coordinator protocol fields (Green, Blue)

`green compute_coordinator.clj:114–115,173–196` · `blue coordinator.py:54–55` ·
`red coordinator.ts:141–142` refuses

Green merges extras after the generated `run_id`, `write_id` and
`target_etag`, and accepts any event type string; Blue spreads `**fields`
last. Red rejects unknown names and reserved keys. Only trusted callers reach
this, but a caller bug can reuse a write id or forge an ETag, and the
coordinator contract promises generated ids never repeat.

### 11. A malformed journal at `acquire` is classified three different ways

`green compute_coordinator.clj:25–30,121,126` · `red coordinator.ts:96,101` ·
`blue coordinator.py:86,101`

Green poisons with "ownership uncertain" and hides that the object is corrupt;
Red throws `invalid lifecycle document` without poisoning; Blue reaches the
reducer with an empty ETag and leaves the phase at `acquiring`. A second
acquire after a poisoned first differs too. Blue also performs a remote read
and consumes a run id before rejecting an invalid identity that Green and Red
refuse in the constructor.

### 12. GCS maps a missing bucket to `absent`, against the transport contract

`green compute_gcs.clj:17` + `compute_journal.clj:139` · `red gcs.ts:11` +
`journal.ts:87` · `blue gcs.py:35–36` + `journal.py:108–109` ·
`contracts/object-transport.md:18–22`

The contract admits `absent` only for a missing key; a missing bucket is an
error, and S3 honours that. On GCS a mistyped bucket makes inspection report
"no deployment", and a bucket deleted out of band makes `state_presence`
report `absent`, which the converge treats as destroyed without running
OpenTofu. The acquire fails first in practice, so the destructive branch needs
a narrow race; the inspection misreport is unconditional.

### 13. GCS 412 is mapped to `conflict` globally, and the three colours then diverge

`green compute_gcs.clj:17` · `red gcs.ts:12` · `blue gcs.py:37–38` · bucket
delete result ignored at `managed_gcs_backend.py:97` and siblings

A 412 on bucket delete returns `destroyed` with the bucket still present. A
412 on bucket create (an org-policy rejection) becomes the metadata value:
Green and Red fail with a misleading "ownership mismatch", Blue crashes with
`AttributeError`. Separately, Red and Blue crash on a `null` listing page
during purge where Green completes with `destroyed`, and Blue's
`state_presence` accepts any 2xx body as `present` where Green and Red require
`generation`.

### 14. Managed-bucket mode is a per-backend flag, and the wrong one is silently ignored

`green compute_managed_backend.clj:96–99` · `red managed-backend.ts:11` ·
`blue managed_backend.py:15–17`

Dispatch happens on `provider-backend` before any mode check, so
`provider-backend: gcs` with `s3-bucket-mode: managed` takes the GCS path,
defaults to external, and returns `skipped`. The bucket is never created and,
on delete, never removed. S3 at least refuses its own flag against a foreign
backend.

### 15. Converge proceeds on an absent presence read with a non-empty pulled state

`green compute_execution.clj:129–133` · `red execution.ts:105–110` ·
`blue execution.py:196–206`

If the pulled state parses and the provider matches, create continues even
though the independent presence probe said absent. A writer racing between
the probe and `tofu init` is not detected. The contract covers "empty with
absent" but not this case.

### 16. SSH reservation semantics diverge and Red/Blue can mask a committed success

`green compute_ssh.clj:80,86–87,148` · `red ssh.ts:36,39,78–79` ·
`blue ssh.py:97,104–105,179–182`

When the lock's identity changed, Green leaves it silently; Red and Blue throw
from `finally`, overriding a prepare whose `record_prepared` already
committed. The lock-exists messages differ, and collision checks run at
different points relative to taking the reservation. No colour tests the
"reservation changed" branch.

### 17. OCI `private` ingress sources cannot resolve at HEAD

`contracts/provider-recipes.json` oci: network_mode discovered, no cidr
options · `red provider-request.ts:72–74` · `blue provider_request.py:75–79` ·
`green compute_request.clj:92–94`

Every format but DigitalOcean resolves `private` to the network CIDR, and OCI
never emits one, so the standard cluster-peer rule shape is refused unless the
caller passes a CIDR by hand. The provider-request contract claims only
`private_filter` is unsupported on OCI. The uncommitted OCI work is addressing
this with an interpolated subnet CIDR, which the literal check would currently
reject.

### 18. Managed Kubernetes never removes the kubeconfig on destroy

`green compute_managed.clj ~191` · `red managed.ts:16` · `blue managed.py:275`
· no unlink in any managed module

Written with mode 0600 under the work directory on create; a cluster-admin
credential file persists after delete in all three colours. Impact is low
once the cluster is gone, but the contract promises private handling and says
nothing about retirement.

### 19. Resume of an interrupted purge skips the foreign-object check

S3: `green compute_managed_backend.clj:71–91`, `red managed-backend.ts:56–73`,
`blue managed_backend.py:116–151` · GCS siblings · purge never re-asserts GCS
soft delete

When the marker is already `deleting`, the live-state scan is skipped and
every generation is deleted. A second profile in external mode that wrote
into the bucket after the interruption loses its state. On GCS, retention
re-enabled out of band (or an org policy) makes every delete produce a
soft-deleted generation, the bucket delete returns 409, and bootstrap is
refused until retention expires.

### 20. The consumer estate is split across 13 library commits, and the workspace gate is red

`workspace/scripts/compute-copy-contracts.py` exit 1 ·
`once/blue/pyproject.toml:15` vs `once/green/deps.edn:5` and
`once/red/package.json:10` · `redis/package.json:13–33`

`once` pins 4f36a7f in its Blue dev group and 5040d93 everywhere else,
committed as f260916. `redis/red` uses the reusable-facade pattern that the
gate allows only for once and neon. Six deployments run payloads older than
their package: clickhouse-hetzner and langfuse-vultr at 6325b24, n8n-vultr and
redis-vultr at 3451a05, automq-vultr at 5040d93, automq-aws at 87ec566 with no
lockfile. The four MySQL and Postgres packages are 25 commits behind. API
drift across the whole range is purely additive, so bumps are behavioural
(the existing-state guard from 5040d93, virgin-state acceptance from 87ec566)
and need a golden review, not code changes.

### 21. The Blue SDK dependency resolves to an unrelated PyPI package without a source pin

`blue/pyproject.toml:6` `blue>=0.1.0` · `HANDOFF.md:52–55` records this exact
defect as fixed before the first publish

PyPI's `blue` is a code formatter at 0.9.x and satisfies the range. Commit
4f36a7f reintroduced the shape to let applications choose the SDK source;
today all 31 Blue consumers carry their own git source, so nobody is exposed,
by convention only. Any future consumer that installs with pip, or drops its
source entry, gets the formatter silently.

### 22. Contracts, README and handoffs describe an R2/S3 library and a September 9 rollout

`README.md:10,52–53` vs `146–163` · `contracts/README.md:15` ·
`contracts/managed-backend.md:12` · `contracts/coordination.md:21` ·
`HANDOFF.md:3,36,80` · `contracts/roles.md:77–79` · 12 handoff files

The README says backends are R2 and S3 and then documents GCS ninety lines
later. No contract mentions GCS at all: the 404 and 412 mappings, the
`<key>/default.tfstate` layout and the generation-precondition journal are
specified only by tests. The root handoff still says no package uses the
library; 33 do. Test counts in every handoff are stale. The roles contract
says role firewalls were never exercised live; the Langfuse AWS run on 10 Sep
did. The DigitalOcean README says reserved IPs, owned VPCs and managed
Kubernetes are out of scope; all three ship. The provider-request contract
omits `none` network mode, `peer_roles`, `endpoint`, `roles`, `ipv6` and
`fingerprint_file`. Twelve handoff files describe superseded slices; one
should survive.

### 23. CI gaps: three test scripts run nowhere, no GCS probe, and today's colours landed in three red pushes

`.github/workflows/checks.yml` · `test/provider-adoption.py`,
`provider-endpoint-schema.py`, `provider-icmp-schema.py` · runs 34590408831,
34590787944, 34590940439

The adoption proof cited by the workspace plan hard-codes a sibling `automq`
checkout with installed node modules and cannot run in CI. The GCS backend has
unit tests but no loopback analogue of the S3 backend, HTTP and journal
probes, and `gcloud` appears in no CI step. The Red-and-contracts, Green and
Blue halves of the GCS change were pushed as separate commits, each failing
`registry.py` on main until the third landed; the workspace rule is that
shared behaviour lands in all three colours in one commit. CI also runs every
provider checker twice, and no `CLAUDE.md` exists in this repository, unlike
every other checkout.

### 24. Provider examples cover a minority of packaged stages

`providers/digitalocean/check.py:34–37,51–54` · `hcloud check.py:34` ·
`vultr check.py:34,44–48` · `yandex check.py:34` ·
`test/fixtures/provider-roles.json` has no DigitalOcean case

The checkers do re-render from templates, so covered examples cannot go
stale, but DigitalOcean's created, none, referenced and all four role stages,
the hcloud and Vultr none stages, and both Yandex dynamic stages are rendered
by no example and no fixture. Four DigitalOcean example directories are
referenced by nothing at all.

## Low

- **Finish ordering and exit interpretation differ:** Green checks ownership before the local-attempt match, Red and Blue the reverse; Red passes an undefined operation id through the local check. Green and Blue reject `4.0` as a state version, Red accepts it.
- **Journal parser drift:** Blue's AWS service-code regex is wider; Red alone rejects U+2028/2029 in credentials; Blue decodes stdout strictly and turns one bad byte into an `error` read.
- **Red derives the journal identity from raw options** while Green and Blue derive it from the backend plan; equal today only because the plan copies options verbatim. The uncommitted OCI work extends this into real derivation logic in two places.
- **Green's schema-2 reducer addresses nodes by keyword only,** masked by the coordinator's keywordisation.
- **Undocumented surface:** `converge_state` accepts a `check` operation and both it and `state_presence` accept the managed-kubernetes key; the tofu-runtime contract lists neither.
- **Recovery interpolates `aws-region` unvalidated** and surfaces a raw null error when it is missing.
- **`ssh-keygen` children inherit the full environment** including `COLORS_PAR_*`; every other child strips them. Key files are chmod'ed before their fingerprints are compared.
- **`shared-destroy` does not require `deleting` status** and is vacuously allowed with an empty node map; unreachable through `orchestrate`.
- **Cancellation:** Green spins until the fan-out settles, Blue shields the task, Red recognises only an `AbortError` nothing in the library raises.
- **Dead code:** the dead delete guards in Red and Blue orchestration, a poisoned check after an exhaustive `cond` in Green, a duplicated credential validation in Blue's journal, an unused import in Green's runtime.
- **GCS concurrency:** bootstrap PATCHes with `ifMetagenerationMatch` every run, so two simultaneous bootstraps fail where S3's idempotent puts succeed; bootstrap returns `ready` when the protection PATCH 404s; Green's HTTP client bounds headers but not body reads; one `gcloud auth print-access-token` fork per journal operation.
- **Finalize accepts different state shapes:** S3 any depth under the profile, GCS only `…/default.tfstate`; a non-default workspace on GCS is refused as unexpected objects.
- **Green's kubeconfig sink checks ownership against the parent directory,** Red and Blue against the current uid. Blue's managed version preflight honours an ambient `HTTPS_PROXY` with the provider token; Green ignores env proxies.
- **Endpoint agent is clean** (byte-identical in four copies, validated inputs, capped response, bounded deadline) but the DigitalOcean token scope it needs on the host is unspecified, and Green has no endpoint test.
- **Managed cleanup scripts fail closed above one API page** (200 DigitalOcean or 500 Vultr volumes or load balancers), and the controller manifest is version-pinned but not checksum-pinned.
- **AWS declares `registration: true` with no collision preflight,** so a duplicate key name fails at apply after a local keypair was already generated. Documented, but a weaker guarantee than the other three registering providers.
- **hcloud accepts IPv6 ingress rules for nodes with IPv6 disabled;** Yandex renders ICMP with null ports though its README says ICMP is unsupported (API acceptance unverified).
- **Hard-coded values siblings parameterise:** OCI discovery OS and version, the `ubuntu` user in Azure, Google and Yandex, disk types on Google, Azure and AWS, `ha: false` on DOKS. `required_version` is declared only by AWS, DigitalOcean and OCI templates.
- **Node result extras are not uniform** (`ssh_key_id`, `metadata`, `uid`, `vpc_id` vary) and deployment tags exist on only four of eight providers, so no generic inventory-by-tag is possible.
- **Unknown stage failure modes differ:** Red TypeError, Blue KeyError, Green renders an empty document set and continues.
- **Packaging noise:** two `colors-compute-red` manifests with different export maps (the `./workflow` subpath is used by no consumer), root `files` ships provider examples and handoffs, all versions 0.1.0 with no tags, the licence names "Colors contributors" where sibling repos say "getcolors".
- **Library SDK pins** (Green 3f33f5d, Red db9bfe6) are behind their heads by one and three commits; both suites pass on the heads, so bumping is safe. Blue tests against SDK ec33f05, newer than any SDK a consumer runs.

## Consumer pins

Colours within a package agree except `once`. "Behind" counts library commits
between the pin and HEAD. Deployment payload pins are listed only where they
differ from the package.

| Package | Pin | Behind | Deployments |
|---|---|---:|---|
| automq | d2c75d7 | 1 | automq-vultr 5040d93 · automq-aws 87ec566, no lockfile |
| clickhouse | b98d88b | 6 | clickhouse-hetzner 6325b24, no lockfile |
| langfuse, n8n, neon-multi-node, redis | 09ec539 | 8 | langfuse-vultr 6325b24 · n8n-vultr, redis-vultr 3451a05 |
| once, walter, rama, alice, github-dwh | 5040d93 | 12 | once Blue dev group 4f36a7f |
| agent-network, temporal | e631834 | 13 | |
| airflow, k3s | 01635b4 | 14 | |
| dbos, posthog, restate, rybbit, signoz, umami, vaultwarden | 422c3f3 | 15 | |
| clickstack, neon, netbird, wavehouse | 3451a05 | 16 | |
| agent-network-k8s, agent-network-doks | 09d1328 | 17 | |
| k8s | 6325b24 | 24 | |
| mysql-agy, mysql-ha, postgres-agy, postgres-ha | 85bf076 | 25 | |

Every pinned SHA is an ancestor of origin/main. No package still carries its
own provider templates or registry; the ONCE-era compute code is gone.

## Verified sound

- The pure reducers (coordination, lifecycle, journal cases, state decisions) agree across colours on all 479 shared cases, including error ordering.
- Credential isolation matches in backend, journal and execution: private INI files, `AWS_*` stripped for R2, 0700/0600 with exclusive create, no secret in argv, URL or generated documents. The loopback probes confirm R2 signs with its own key and sends no ambient session token.
- GCS preconditions are correct in all three colours (`ifGenerationMatch=0` on create, the observed generation on update, 412 as conflict, read-back on ambiguity), the OpenTofu prefix layout matches the presence probe, and purge deletes every generation before the marker and the bucket.
- Bootstrap precedes every state read; finalize requires an explicit `compute-prevent-destroy: false`, a retired journal and empty states; `compute-require-existing-state` guards bucket and journal creation identically.
- Managed Kubernetes keeps its own schema and refuses VM-schema journals; power start and stop agree on read-before-mutate, one mutation, bounded polling and lease retention on uncertainty.
- Packaged registries, recipes, options and templates are byte-identical to the canonical files, and every packaged file has a drift check.

## Suggested order of work

1. **Lifecycle exits.** Add a reducer transition from `deleting` with an absent key straight to `retired` when every record is `declared`, let a declared node with an empty present state be marked destroyed, and let delete verify the key only when it will be used. Land all three in one commit with shared fixtures, since these paths have none.
2. **Documented lock recovery.** Either a reviewed `release` path for stuck key phases or a written manual procedure in the contract; today there is neither.
3. **GCS owner assertion.** Compare `projectNumber` to the configured project on every bucket read, and map 404 on the bucket to `error`. Then write the GCS sections of the object-transport and managed-backend contracts from the tests that already exist.
4. **Red packaging.** Move `red` to `peerDependencies`, bump the dev pin to e24217c and Green's to a918861 (both suites already pass), republish, and bump consumers so their pinned SDK fix reaches the join.
5. **Templates.** `prevent_destroy` on AWS network and key pair and the OCI NSG; `ignore_changes` on the OCI discovered image, or record and pin it in the journal as the README promises.
6. **Estate hygiene.** Resolve the `once` split and the `redis/red` gate rule, refresh the six lagging payloads, then plan the four database packages' 25-commit bump with a golden review.
7. **Docs and CI.** Collapse twelve handoffs into one current status file, fix the README's backend sentence and the contract error strings, add a `CLAUDE.md`, wire the three orphaned test scripts or delete them, and add a GCS loopback probe.

Method: full local check run on the clean tree, then five parallel code
reviews (runtime, providers, docs and CI, consumers, GCS and managed layer),
each verified against `git show HEAD:` after the working tree went dirty, and
the seven high findings re-read by hand. Nothing in any repository was
modified.
