# Colors compute handoff

Updated 2026-09-09. See `colors-compute-implementation.md` for the full plan.

The user authorized implementation, cluster-first package migration, subagents,
commits and pushes to main, and live deployments when needed. Write this file
before stopping, even when work remains incomplete.

## Current state

- Standards, plan, and cluster inventory were committed and pushed to
  `getcolors/workspace/main` as `873f384`.
- `getcolors/colors-compute` was created. Its first foundation commit `a112e17`
  was pushed to main, and GitHub Checks passed for that commit.
- Green, Red, and Blue implement common contracts and actual SDK fan-out/join
  composition. Pure backend planning keeps R2 binding names separate from
  ambient AWS compute credentials.
- Eight provider template sets have passed credential-free OpenTofu 1.12.5
  schema validation. Their versions and limitations are documented in each
  provider README. Runtime cloud operations are not implemented yet.
- Packaged provider loaders and OCI/Yandex templates were pushed as
  `1cf448db814773e56d9f7afb89bd814574c8f6c1`. Shared parity passes 129
  cases per color, including packaged provider plans against validated examples.
- Its GitHub contracts job and all eight provider schema jobs passed:
  https://github.com/getcolors/colors-compute/actions/runs/34353691140
- Published Git dependency smoke checks passed in temporary directories outside
  the workspace for all three colors. Blue's built wheel also loads packaged
  templates and the SDK without local-source overrides.
- No package migration or live operation has occurred. Cluster packages remain
  first in rollout order. The inventory is `colors-compute-cluster-inventory.md`.
- Unrelated workspace changes are recorded in the plan and must be preserved.

## Remaining work

1. The packaged provider-plan milestone is complete and published. The
   production library and consumer rollout are not complete.
2. Implement protected backend credential binding and cache handling, remote
   state reads that distinguish absence from errors, deployment coordination,
   and persistent ownership records before enabling provider mutations.
3. Implement shared SSH/network lifecycle, capability and semantic validation,
   single-node apply/destroy, SSH readiness, retries and scale-down cleanup.
4. Migrate AutoMQ first with explicit state mapping. Continue the other cluster
   packages, then migrate single-host packages. No consumer should pin the
   foundation as though it were a completed compute lifecycle.
5. Prove version-only provider adoption, complete required package checks, and
   migrate installed deployment launchers only with reviewed state procedures.

Final implementation check counts: Blue 41 tests; Green 14 tests / 90 assertions;
Red 24 tests / 109 assertions plus typechecking; 129 parity cases per color.
Registry/template copies and deterministic provider examples pass checks.

The read-only AutoMQ migration planner has 7 passing synthetic tests. It never
fetches or writes live state and always marks plans non-executable. It is a
review tool, not a state-transfer implementation.

The Blue wheel initially resolved the unrelated PyPI `blue` package outside
the checkout. Its package metadata now contains the immutable Colors SDK Git
dependency, and the external wheel smoke check passes. This packaging check
must remain part of publishing evidence.

Consult `colors-compute/HANDOFF.md` and language/provider handoffs for current
APIs and check counts. Agent runs were interrupted by usage limits; inspect
working-tree status before resuming and do not assume an interrupted task
completed its validation.

## Live resources

None created or changed by this task.

## Published runtime and journal contracts

Library commit `fba3e4ceaa647f7590754e93eac3bf8921846935` is pushed to main.
It adds protected read-only backend sessions and pure conditional journal
transitions in Green, Red, and Blue. Current local suites passed Blue 130 tests,
Green 26 tests / 283 assertions, Red 89 tests / 309 assertions, and 211 shared
parity cases per color. Real OpenTofu loopback tests verified private R2 binding,
ambient AWS separation and native state reads. A deterministic 4,608-case
mutation audit found no cross-color coordination mismatch.

[GitHub Checks](https://github.com/getcolors/colors-compute/actions/runs/34356072900)
passed. The AWS schema job initially received a GitHub HTTP 500 downloading the
provider signature; its retry passed. No validation was skipped to get a pass.

Work is continuing on the conditional journal transport described in
`colors-compute/contracts/object-transport.md`. It uses AWS CLI 2 to preserve
S3's ambient credential chain and private backend-only R2 credentials. An
HTTPS loopback probe will test actual conditional writes. A transport result
must not dispatch provider work until the coordinator establishes ownership.
No package or live deployment has migrated; cluster packages still go first.

## Conditional transport checkpoint

Library `5ffa2a17b36e7f5113b20efd34a53cf6f222985c` is pushed to main. It adds
journal get and conditional put in all three colors, with private AWS CLI
backend sessions and strict write identity/condition validation. S3 uses the
ambient AWS chain; R2 uses a private backend-only credentials file. Only exact
GetObject NoSuchKey proves absence; write errors remain ambiguous until the
coordinator reads back the intended write_id.

Local validation passed: Blue 186 tests; Green 37 tests / 403 assertions;
Red 100 tests / 415 assertions and typechecking; 248 shared parity cases per
color. The actual AWS CLI HTTPS loopback probe passed in each color: one winner
among two simultaneous acquisitions, a successful conditional update, and a
refused stale update. It observed only seven expected requests per color,
with correct R2 signing and no ambient AWS session token. No live service,
state or deployment was used. The contracts job and all eight provider schema
jobs passed in [GitHub Checks](https://github.com/getcolors/colors-compute/actions/runs/34357566145).

The library's new generic prerequisite is AWS CLI 2 with conditional PutObject
support, tested locally with 2.35.11. Add this prerequisite when consumers
migrate; adding a compute provider later must not require package changes.
The current native runtime targets POSIX environments, as do its private-file
and process-group controls. Neither the transport nor pure journal rules
constitute complete orchestration.

Next implementation:

1. Build a single coordinator over the journal transport. Serialize transitions;
   generate unique run/write/attempt IDs; confirm ambiguous writes by exact
   document/write_id readback. Stop new dispatch on ownership uncertainty.
2. Wrap the actual Colors fan-out so each node's durable start intent precedes
   dispatch and every terminated attempt records its outcome. Track active
   children; keep the lock on cancellation or uncertainty until safe recovery.
3. Extend the journal's currently limited transitions for shared key/network
   ownership, retry, scale-down, destruction and retired deployment records.
   Implement those lifecycle operations before migrating AutoMQ.
4. Migrate the cluster packages first, prove version-only provider adoption,
   then migrate single-host packages and installed deployment launchers.

No additional permission is needed for the already-authorized implementation,
commits, main pushes or disposable validation. Preserve the unrelated workspace
changes listed above. Keep writing this handoff before stopping.
