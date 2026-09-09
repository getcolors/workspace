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
- Packaged provider loaders and remaining OCI/Yandex templates are being
  prepared for the next library commit. Shared parity currently passes 124
  cases per color, including packaged provider plans against validated examples.
- No package migration or live operation has occurred. Cluster packages remain
  first in rollout order. The inventory is `colors-compute-cluster-inventory.md`.
- Unrelated workspace changes are recorded in the plan and must be preserved.

## Remaining work

1. Finish publishing and checking the packaged provider-plan milestone.
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
