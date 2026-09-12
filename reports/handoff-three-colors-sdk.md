# Three-colour SDK handoff

Updated 2026-09-12. Continue with captured-command interruption, then renderer
parity. The inherited-terminal failure fix is complete. Singleton fan-out
needs an explicit join contract before a scheduler change.

## Workspace and instructions

The workspace is `/home/ubuntu/code/getcolors`. It is not a Git repository.
`green`, `red`, `blue`, `once`, and `workspace` are separate repositories.
Paths below are relative to that workspace unless stated otherwise.

Read `CLAUDE.md` at the workspace root and the instructions in each repository
before editing. Blue also requires reading its README. Green is the canonical
SDK behavior, except where the report identifies a shared defect.

The user authorized commits and pushes to `main`, requested subagents, and
said not to ask more questions. Use separate language implementation agents
after agreeing on the interrupt contract. Have another agent review the
combined behavior. These instructions do not authorize live cloud deployment
or destruction.

The user also requested the `unslop` skill. Load it with:

```sh
npx skills use "https://github.com/cursor/plugins" --skill "unslop" > /tmp/getcolors-unslop-instructions.txt 2>&1
cat /tmp/getcolors-unslop-instructions.txt
```

Read the complete output and resolve supporting files from the directory the
command provides. Apply its plain-language rules to documentation and updates.

## Completed and pushed

| Repository | Commit | Change |
|---|---|---|
| Red | `6f640e681a743f0e2c3238cb1913a047381b84a5` | Added `runtime.execInherit` and normalized inherited process failures. |
| Blue | `7488028bf93bfcd74f3645fd9b3eb34eca9676d9` | Added `runtime.exec_inherit` and the equivalent failure handling. |
| Workspace | `7335c3e` | Corrected the audit and recorded the fixes in `reports/three-colors-sdk.md`. |

Red's public `runInherit` stays asynchronous. Blue's `run_inherit` stays
synchronous. Both delegate to replaceable runtime methods and inherit terminal
streams. Missing executables return 127. Negative signal statuses become
`128 + signal`, so SIGTERM returns 143. Workflow successors no longer run after
these failures. Blue also supports removing inherited environment variables
with `None` overrides.

The implementation and regression tests are in:

- `red/src/process.ts`, `red/src/runtime.ts`, and `red/test/process.test.ts`.
- `blue/src/blue/process.py`, `blue/src/blue/runtime.py`, and `blue/tests/test_process.py`.

The docs describe both runtime methods. Red's inherited execution still does
not implement `timeoutMs`. The captured-command cancellation code was not
changed. No downstream package or deployment pins were updated.

## Verification already completed

- Red passed 126 tests and typecheck. Two optional integration tests skipped.
- Blue passed 136 tests. Two optional integration tests skipped.
- Real subprocess tests cover missing executables, self-SIGTERM, ordinary
  exits, runtime replacement, and failure propagation that stops successors.
- A direct Green probe returned 127 for a missing executable and 143 for SIGTERM.
- ONCE's complete `scripts/parity.sh` passed with local SDK overrides in a
  temporary copy. It checks generated artifacts and existing workflow contracts.
  The SDK process tests cover inherited failures, which ONCE parity does not.

The temporary ONCE copy is `/tmp/getcolors-inherited-parity-0_bw8uj8`.
Its output is `/tmp/getcolors-inherited-parity.log`. These files may disappear.
The copy used local module links for Red, a local dependency in Green's
`bb.edn`, and `PYTHONPATH` for Blue. `UV_NO_SYNC=1` prevented uv from replacing
the selected environment. Confirm actual import paths when recreating it.
Do not count a parity run against old pinned SDKs as verification of new code.

Green's full suite and live examples were not rerun for the inherited fix.
The two Red and Blue skips were the opt-in floci integration and the Ansible
inventory round-trip. Explicit Ansible installation in CI remains open.

## Next task: captured-command interruption

Start with report finding 6. Inspect `green/src/green/process.clj`,
`red/src/runtime.ts`, `blue/src/blue/runtime.py`, and each SDK's CLI entry point.

Green uses `setsid` for captured commands when the required tools exist.
Those children leave the terminal's foreground group and can outlive the
launcher. Its thread-interruption cleanup and `future-cancel` tests do not
establish OS SIGINT behavior. Blue starts captured commands in a new POSIX
session. `asyncio.run` cancellation currently leads to immediate SIGKILL of
that group. Red detaches timed captured commands and has no launcher interrupt
handler. Untimed Red commands share the terminal group.

Implement and document this POSIX contract:

1. Forward the first launcher SIGINT once to each active detached process group.
   Do not duplicate the terminal's delivery to commands sharing its foreground group.
2. Keep output readers alive during a bounded grace period so children can clean up.
   Choose and document the grace duration. Kill survivors after that deadline
   and bound the remaining wait for retained output pipes.
3. Preserve launcher exit 130 and stop workflow successors even if a child's
   interrupt handler exits successfully.
4. Track concurrent commands through a shared lifecycle mechanism. Restore
   handlers and remove process entries after completion. Blue cleanup must
   survive task cancellation; Green needs OS shutdown integration.

Keep timeout behavior separate from user interruption. Windows console
delivery needs separate implementation evidence and tests. Forced `taskkill`
does not establish graceful interruption.

Test actual workflow launcher subprocesses. Wait for a readiness marker before
signaling the launcher's process group. A synthetic child should record SIGINT,
delay briefly, write a cleanup marker, and exit. Assert the marker, launcher
exit 130, and no successor execution. Also cover an interrupt-ignoring child,
concurrent branches, surviving descendants, timed and untimed commands, and
descendants that retain output pipes. Clean up every test process.

These tests prove signal and cleanup behavior. They do not prove OpenTofu
state recovery or corruption. The audit demonstrated neither.

## After interruption

Fix Red and Blue renderer parity against real Selmer. Empty strings and the
literal string `"false"` must be false inside `if`. Apostrophes must escape as
`&#39;`. Unknown filters must fail rather than silently pass through values.
Add focused SDK tests and downstream fixtures for the affected values. Preserve
alternate template delimiters that leave Ansible's Jinja expressions intact.

Handle JSON byte parity separately. Red's locale ordering and Blue's ASCII
escapes can change file bytes without changing parsed values. Decide HCL map
ordering across all three SDKs and test the selected contract. Do not describe
serialization differences alone as proven infrastructure state changes.

For singleton joins, adding a fork frame alone is insufficient. The current
`same-origin?` and `step-units` logic still runs one entry as an ordinary step.
The proposed design maps a fork step to its intended join explicitly. Preserve
fork-point opts, run intermediate branch steps normally, and invoke the declared
join with zero, one, or several branch results. Failed forks and explicit end
bounds still stop. Preserve existing implicit joins for compatibility.
This is a proposed API, not an implemented or finalized contract.

Test zero, one, and three branches, distinct fork and branch opts, multiple
intermediate steps, failed singleton branches, nested joins, and ordinary
linear routing. Update examples to declare joins when the API is implemented.
Embedded dry-run propagation is a separate shared issue.

## Validation and delivery

Run the applicable commands from each repository:

```sh
# green
bb test
clojure -X:test

# red
bun test
bun run typecheck

# blue
uv run pytest

# once, with the edited SDKs actually selected
bash scripts/parity.sh
```

Check branch and working-tree state before each edit and commit. The workspace
repository has unrelated local changes and has received other commits since
the SDK report commit. Stage only this task's files. Preserve unrelated work.
Push SDK commits before any consumer pin update. Use the package's `bb pin`
workflow for consumer launchers rather than inventing or hand-editing SHAs.

Update `workspace/reports/three-colors-sdk.md` with actual commits, executed
checks, skips, and remaining issues. Keep its root copy `three-colors-sdk.md`
consistent. The report's source line references describe the original audit
commits and may have moved. Its scalar-parity result uses normalized fixture
descriptions and does not prove identical runtime types or complete YAML support.

The tracked copy of this handoff is
`workspace/reports/handoff-three-colors-sdk.md`. The requested workspace-root
copy is `handoff-three-colors-sdk.md`.
