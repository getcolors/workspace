# Colors compute handoff

Updated 12 September 2026.

## Current state

The audit review and first remediation pass are complete and pushed to main.
Consumer dependency pins and deployment payloads have not been updated. The
next task is to adopt the library fixes in consumers, starting with one package.

| Repository | Pushed commit | Contents |
|---|---|---|
| `colors-compute` | `2e55b05c94da2835bd4914076ef0845140dab71f` | Lifecycle deletion fixes, recovery procedure, GCS ownership checks, Red packaging |
| `workspace` | `d719c7f8190f8a8c3ac7fa5ca399c5246e332f56` | Reviewed audit and remediation record |

Both CI workflows passed:

- [Compute checks](https://github.com/getcolors/colors-compute/actions/runs/34685975148), including all eight provider schema jobs.
- [Workspace checks](https://github.com/getcolors/workspace/actions/runs/34685987129).

Read [the audit](reports/colors-compute.md), especially its review and remediation
sections. Its original findings and consumer inventory describe commit
`4f36a7f` and the September 11 workspace. Recheck current pins before editing.

## Completed changes

- Finding 1. Delete before key preparation now verifies absent or empty state,
  records destruction, and retires without SSH or compute operations.
- Finding 2. Commit `bd82520` had already fixed deletion of declared nodes with
  retained empty state. This fix predates the current remediation.
- Finding 3. Interrupted key phases still retain their locks. The new manual
  recovery procedure requires process termination, provider and state checks,
  and a conditional journal repair with exact read-back verification. It also
  covers a held lock after key removal. No automatic takeover was added.
- Finding 9. Prepared deployments can delete without local key files. Destroy
  rendering uses a fixed valid public key. Cleanup still verifies surviving
  managed files against the journal fingerprint and refuses foreign files.
  Delete also resumes retirement after key removal has committed.
- Findings 4 and 12. Managed GCS verifies the bucket's project number against
  Resource Manager before mutation. An object 404 counts as absence only after
  a separate read confirms the bucket exists.
- Finding 5. Both Red manifests declare the SDK as a peer. The Red development
  SDK pin is `e24217c32ab00ffd29d4767a53c880795f86f977`. Green uses SDK commit
  `a918861`; obtain its full SHA from `colors-compute/green/deps.edn` when needed.

Relevant contracts:

- [Manual key-phase recovery](../colors-compute/contracts/key-phase-recovery.md).
- [Lifecycle journal](../colors-compute/contracts/lifecycle-journal.md).
- [Orchestration](../colors-compute/contracts/orchestration.md).
- [Managed GCS backend](../colors-compute/contracts/managed-gcs-backend.md).

## Adoption requirements

Red consumers must retain an explicit Getcolors Red SDK Git dependency. The
peer range is `*`; it does not choose the Getcolors repository. Bun 1.3.10 hung
on `^0.1.0` in an isolated installation check. The wildcard configuration passed
with both installed archives and an explicitly pinned Git SDK consumer.

`colors-compute/scripts/red_package.py` checks both package layouts using the
actual installed SDK and library archives with a temporary Bun cache. CI runs
it after the frozen Red install. Keep the isolated cache, since an earlier
shared-cache installation hung intermittently and its cause was not established.

Managed GCS now requires `resourcemanager.projects.get`. Readers also need
`storage.buckets.get` to distinguish a missing object from a missing bucket,
including readers of external buckets. Review these permissions before adopting
the change in a GCS deployment.

## Next work

1. Inspect current consumer pins and choose one representative three-colour
   package. The audit identified a split pin in `once` and a copy-contract issue
   in `redis`, but their current status needs verification.
2. Update all three library pins to the published compute commit above. Refresh
   lockfiles and keep an explicit reviewed SDK Git pin in Red. Verify that the
   consumer and compute orchestration resolve the same Red SDK module.
3. Run that package's language suites, parity checks and golden comparisons.
   Inspect the golden diff instead of accepting it merely to make tests pass.
   Run the workspace compute-copy contracts after dependency changes.
4. Commit and push the package, then repeat for the remaining consumers. Refresh
   deployment payloads after their package commits are published. Keep root
   launchers consistent with installed payloads. Do not fabricate lockfiles for
   manually copied payloads.
5. Fix OCI image discovery so publishing a newer image cannot block
   reconvergence. Then add the missing AWS network/key-pair and OCI NSG template
   destruction guards. Land shared behaviour in all three colours together.

No live deployment create, delete, state migration, or key recovery was performed
or authorized by the previous code-change task. Dependency and payload updates
do not transfer existing state.

## Review corrections to preserve

All three executors reject replacement plans before apply, even with
`compute-prevent-destroy=false`. Findings 6 and 7 therefore do not establish
automatic VM replacement through the library. OCI image discovery can still
block reconvergence, and the missing template guards remove an extra protection
for direct template use.

Duplicate SDK instances are a real packaging problem. The audit did not prove
an additional `StepError` exit-code regression in orchestration, which already
catches node exceptions and returns exit code 1. Do not repeat that impact claim
without a reproduction. The historical severity totals have not been recalculated.

## Validation completed

- Blue: 591 tests passed.
- Red: 362 tests and typecheck passed.
- Green: 132 tests and 1,539 assertions passed.
- Shared parity: 496 cases per colour passed.
- Both Red installed-package layouts resolved one consumer SDK copy.
- Backend, journal, managed cleanup and power HTTPS probes passed.
- Registry, packaged resources, migration, network and compute-option checks passed.
- OpenTofu accepted the destroy-only public key in representative configurations
  for all eight providers. CI also passed all provider schema jobs.

The cloud-related local checks used synthetic credentials. They do not establish
live account permissions or prove a live deployment rollout.

## Workspace and working rules

`/home/ubuntu/code/getcolors` contains separate repositories. Read each target
repository's instructions before editing it. The compute checkout was clean
after the push. Leave these unrelated workspace changes intact:

- Modified `scripts/package-copies.py`.
- Untracked `card-prompt.md`.
- Untracked `reports/repository-audit-2026-09-11/`.
- Untracked `reports/sdk-audit-2026-09-11/`.
- Untracked `scripts/__pycache__/`.

The user authorized commits and pushes to main, requested subagents, and asked
not to receive further questions. The requested `unslop` skill was loaded with
`npx skills use "https://github.com/cursor/plugins" --skill "unslop"` and applied
to new prose. Its complete output remains at `/tmp/getcolors-unslop.txt` for this
session. Keep prose plain and preserve unrelated work.
