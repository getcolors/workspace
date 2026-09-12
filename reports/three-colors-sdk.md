# Three-colour SDK audit

Audit of the three workflow-engine SDKs, 2026-09-11, reviewed on 2026-09-12.
The original audit made no repository changes. The findings and source line
references below describe the audited commits, not subsequent fixes. The
review corrected the coverage claims, severity rationale, scalar-parity
conclusion, and proposed singleton-join fix. Remediation status appears below.

## Remediation on 2026-09-12

Finding 1 is fixed in Red and Blue and pushed to each repository's `main`.
The public inherited-terminal runners now delegate to mutable runtime methods.
Missing executables return 127, and negative child signal statuses become
`128 + signal`. Red keeps its asynchronous API and Blue keeps its synchronous
API. Both still inherit terminal streams.

| Repository | Commit | Verification |
|---|---|---|
| Red | [6f640e6](https://github.com/getcolors/red/commit/6f640e681a743f0e2c3238cb1913a047381b84a5) | 126 tests passed, 2 optional integration tests skipped. Typecheck passed. |
| Blue | [7488028](https://github.com/getcolors/blue/commit/7488028bf93bfcd74f3645fd9b3eb34eca9676d9) | 136 tests passed, 2 optional integration tests skipped. |

New regression tests run real missing executables and self-terminating
children. They require exits 127 and 143 and verify that workflow successors
do not run. Tests also cover normal exits and replacement of the runtime
methods. Blue additionally checks inherited output and environment overrides.
A direct Green probe confirmed exits 127 and 143 for the same failure classes.

ONCE's complete `scripts/parity.sh` passed in a temporary copy with the edited
Red and Blue SDKs and the current Green SDK. The copy selected local Red
through module links, Blue through `PYTHONPATH`, and Green through a local
dependency. The check covered generated files, normalized scalar descriptions,
container resolution, SSH behavior, compute behavior, and workflow ordering.
It does not exercise inherited process failures. The new SDK tests cover those.

Subagents implemented each language fix and reviewed the final changes.
The review and documentation edits followed the requested `unslop` skill.
Green's full suite and the live examples were not rerun during this
remediation. No downstream dependency pins changed, so existing pinned
consumers require a later update to receive the fix.

Captured-command interruption, renderer parity, and singleton joins remain
open. The follow-up contracts below describe their required behavior and
tests. The findings below retain the original audit baseline.

## Audit baseline

| Colour | HEAD | Suite | Notes |
|---|---|---|---|
| green | `a918861` | 117 tests pass under bb and JVM | `docco.html` last regenerated 2026-08-08 |
| red | `e24217c` | 121 pass, 2 skip; `tsc --noEmit` clean | |
| blue | `ec33f05` | 130 pass, 2 skip | `uv lock --check` clean |

At audit time, all three checkouts matched `origin/main`. The original audit
reported that every example launcher in every
colour completes `create --dry-run`, `create`, a second idempotent `create`,
and `delete`. The generated trees for `zookeeper`, `multi-zookeeper` and `once`
are byte-identical across colours (tofu-owned state and lock files excluded).
The two skips reported for Red and Blue are the opt-in floci end-to-end test
and the `ansible-inventory` round-trip. The latter skipped locally because
`ansible-inventory` was not on `PATH`. The CI workflows do not explicitly
install Ansible. CI logs or the runner's installed-tool inventory are needed
to establish whether that test skips in CI.

## Verdict

The scheduler and advice engine are faithful line-for-line ports of green,
including the join fixes present at the audited commits. The original audit
reported agreement across 25 scenarios. The problems cluster at the edges the parity fixture never touches:
the subprocess seam, the two hand-written Selmer look-alikes, and JSON
emission. Two of those problems are live in shipped package templates today.
Rendering and serialization differences include apostrophes, uppercase keys,
non-ASCII characters, floats, and empty strings. Process interruption,
singleton joins, embedded dry-run propagation, and frozen values have separate
triggers described below.

## Findings

The original finding numbers are retained for reference. Each finding states
its severity. Findings 3 and 4 are Medium because the audit demonstrated byte
differences without a resulting infrastructure change.

"Reproduced" means a throwaway script showed the behaviour; "verified" means
the cited lines were read and match the claim.

**1. An inherited-terminal command that fails to start, or dies of a signal, counts as success**

Red and Blue. High severity.

`runInherit` and `run_inherit` return exit `-1` when the executable is
missing, and blue also returns the raw negative signal code. The engine's
failure test is `exit > 0`, so the step succeeds, successors run, and the
workflow finishes clean. Green returns 127 for a missing executable and 143
for a child terminated by SIGTERM. Thread interruption returns 130. The normalisation
commits (red `7636bee`, blue `e29a7fc`) fixed the captured path only.
Consumers forward the value straight into the exit key: agent-network-k8s,
agent-network-doks, k3s, k8s, postgres-ha, postgres-agy, temporal.

- `red/src/process.ts:10`, `blue/src/blue/process.py:13`, `green/src/green/process.clj:200`
- Reproduced in both colours (missing binary → exit -1, `failed()` false; blue SIGTERM → exit -15).

**2. An empty string is true inside `{% if %}`; Selmer says false**

Red and Blue. High severity.

The red and blue renderers treat only null and false as falsy. Selmer also
rejects the empty string and the literal string `"false"`. This is live: the
clickhouse package guards on `clickhouse-backup-bucket` and automq on
`automq-apt-security-mirror`, both string-valued. A deployment that sets
either to an empty string renders the block in red and blue and skips it in
green, with no error anywhere.

- `red/src/renderer.ts:237`, `blue/src/blue/renderer.py:255`
- Reproduced through real Selmer, bun and uv with the same template.

**3. Red sorts JSON and HCL keys by locale, green and blue by code point**

Red. Medium severity.

`backend.tf.json`, `constructsJson` and `hclMap` use `localeCompare`. For the
same s3 backend map green and blue emit `Name, Z, a-b, a_b …` and red emits
`… a_b, a-b … Name, Z`. Any uppercase key (an AWS `Name` tag), a
dash-underscore mix, or non-ASCII character can change generated bytes.
That violates the workspace's byte-compatibility requirement. JSON object
ordering alone does not establish an OpenTofu state or resource change, and
the audit did not demonstrate such a change.
Latent today because every current caller uses lowercase keys. Separately,
`hcl-map` order is three-way divergent: green keeps insertion order, blue
sorts by code point, red by locale.

- `red/src/tofu.ts:83,199`, `green/src/green/tofu.clj:102,244`, `blue/src/blue/tofu.py:81,197`
- Reproduced with one fixture through all three; verified in source.

**4. Blue writes non-ASCII JSON escapes such as `\u00e9`**

Blue. Medium severity.

Five `json.dumps` calls keep the default `ensure_ascii=True`: the pretty
backend and constructs writer, `hcl_list`, `hcl_map`, and the Ansible `-e`
extra-vars. Green and red emit raw UTF-8. The one call that already passes
`ensure_ascii=False` (`_python_literal`) shows the intent. Latent until a
`colors.yml` holds a non-ASCII value. A JSON consumer decodes `"\u00e9"` and
`"é"` to the same string, so
this evidence does not establish a changed Ansible value or infrastructure
state.

- `blue/src/blue/tofu.py:100,104,189,196`, `blue/src/blue/ansible.py:93`
- Reproduced; verified in source.

**5. Apostrophes escape as `&#x27;`; Selmer emits `&#39;`**

Red and Blue. High severity.

Every default-escaped `{{ value }}` containing an apostrophe renders
different bytes in red and blue than in green. The same escaping is applied
to scaffold target paths in all three colours, so a path with an apostrophe
differs too, and a path with an ampersand is wrong in all three.

- `red/src/renderer.ts:58`, `blue/src/blue/renderer.py:44`, `green/src/green/scaffold.clj:32,49`
- Reproduced through real Selmer, bun and uv.

**6. Captured commands do not receive graceful terminal interruption consistently**

Green, Red, and Blue. High severity.

When both `setsid` and `kill` are available, Green's new process layer
wraps captured commands in `setsid --`,
putting it in its own session with no controlling terminal. A terminal
interrupt signals the foreground group, which the child has left. The
reproduction showed that the child missed SIGINT and outlived its launcher.
It may later fail when writing to closed output pipes. Blue starts a new
session on POSIX too, but cancellation SIGKILLs the group without giving
the command a SIGINT cleanup opportunity. Red detaches only timed commands and has
no interrupt handler, so those are orphaned like green's. Untimed red
commands still share the group and get SIGINT normally. Packages using these
execution modes inherit the behavior. The audit did not test OpenTofu state
recovery or demonstrate state corruption.

- `green/src/green/process.clj:66-79`, `blue/src/blue/runtime.py:29,80`, `red/src/runtime.ts:45`
- Reproduced in green (child never received SIGINT and outlived the launcher); blue and red verified in source.

**7. A non-UTF-8 byte in command output throws out of the subprocess seam**

Blue. High severity.

The success path decodes stdout and stderr strictly; only the timeout path
uses replacement characters. Tofu and Ansible steps rely on `runtime.exec`
always returning a result. One Latin-1 byte from a remote host turns into a
step failure with a Python trace instead of a captured result. Green decodes
with replacement and never throws.

- `blue/src/blue/runtime.py:107`
- Reproduced (`UnicodeDecodeError` inside a workflow, exit 1).

**8. A one-item dynamic fan-out reaches its join without branch results**

Green, Red, and Blue. Medium severity.

With one successor the scheduler creates a plain unit, not a fork frame. The
downstream join step then runs once as an ordinary step: no branches key, and
it receives the branch's opts instead of the fork point's. Every join in the
examples reads the branches key. A one-server ZooKeeper renders an empty
member list. A one-node floci run hands Ansible no IP. Zero successors
silently skip the join. The three schedulers share this code path.

- `green/src/green/workflow.clj:249`, `red/src/workflow.ts:419`, `blue/src/blue/workflow.py:443`
- Reproduced in green (N=3 has branches, N=1 has none, N=0 never runs the join); red and blue verified as the same branch of code.

**9. A scoping in-function silently switches off dry-run for the embedded workflow**

Green, Red, and Blue. Medium severity.

The engine re-stamps the inherited advice registry after a custom
in-function rebuilds opts, but not the dry-run or event flags. The docs say
to carry them by hand. The failure mode is the opposite of what a flag named
dry-run promises: the sub-workflow runs for real with no warning.

- `green/src/green/workflow.clj:424-445`, `red/src/workflow.ts:633`, `blue/src/blue/workflow.py:648`
- Reproduced in green; same documented behaviour in red and blue.

**10. Credential overlay types only booleans and integers, and only for keys already present**

Green, Red, and Blue. Medium severity.

The docs promise coercion "to the type of the value it replaces". In practice
floats, keywords and collections stay strings, an unparsable integer override
silently stays a string, and a key that exists only in a package's defaults
is never typed because preflight merges defaults under the already-overlaid
opts. Consequence: `COLORS_PAR_COMPUTE_PREVENT_DESTROY=false` cannot lift a
guard that lives only in defaults. Safe direction, but the documented
override does not work. The three colours agree on these rules, so this is a
shared contract gap rather than a divergence.

- `green/src/green/cli.clj:42-53`, `green/src/green/lifecycle.clj:17`
- Reproduced in green; overlay rules executed identically in all three.

**11. The frozen-input change reaches outside the step boundary**

Red and Blue. Medium severity.

Red freezes nested values in place, so a caller-owned config object shared
across runs becomes read-only after the first run, and results come back
frozen. Blue hands steps `FrozenDict` and `FrozenList` and returns them,
which breaks `yaml.safe_dump` and `copy.deepcopy` on any opts subtree. Both
now reject non-plain values (Buffer, Date, datetime, Path, dataclasses,
pydantic models), and the rejection fires one step after the value was
stored, attributed to the consumer, with no key name. This is a behaviour
change waiting for downstream on the next pin bump.

- `red/src/workflow.ts:270-286,348`, `blue/src/blue/workflow.py:272-301`
- Reproduced in both.

**12. Numbers lose their shape in red**

Red. Medium severity.

JavaScript has one number type, so a whole-valued float renders as an
integer everywhere: templates, backend JSON, HCL helpers, inventories,
extra-vars, provider env. Integers above 2^53 are silently rounded where
green refuses the file with a clear message and blue is exact. The parity
fixture normalises `whole-float` to an int in all three describers, so the
existing net hides this on purpose.

- `red/src/cli.ts:102`, `red/src/renderer.ts:65`, `green/src/green/cli.clj:104`
- Reproduced through all three.

**13. Selmer features silently do nothing in the two ports; one documented feature does not exist in Selmer**

Red and Blue. Medium severity.

Unknown filters pass the value through unchanged, so `|upper`, `|length`,
`|join`, `|default` and `|sort-by` are no-ops instead of errors. `forloop.*`
renders empty; `{% elif %}`, `not`, comparisons and `{% comment %}` take the
wrong branch; unclosed tags pass through. Conversely `sort(attribute='…')` is
documented in all three repos and tested in red, yet Selmer rejects it. No
shipped template uses any of these forms today, so the exposure is to the
next template author.

- `red/src/renderer.ts:181-201,356`, `blue/src/blue/renderer.py:194-207,373`
- Reproduced case by case against real Selmer.

**14. Small library contracts disagree in ways a package can observe**

Green, Red, and Blue. Medium severity.

- Inventory host order: green keeps the caller's order, red and blue sort by name.
- Successful command plan: green returns the last command's output, red and blue return empty output.
- An env entry set to nil: green exports an empty string, red and blue unset the variable; a non-string env value raises in blue.
- YAML merge keys: red and blue resolve `<<`, green keeps a literal key. Red also ignores explicit tags, accepts signed hex, and stringifies non-string keys.
- Empty `COLORS_PAR_PROFILE`: green refuses, red and blue accept.
- Provider env booleans: blue emits `True` where green and red emit `true`.
- Above eight distinct live steps green's branch order becomes hash order; red and blue keep insertion order.
- Green's timed runner treats any surviving session member as still running, so a command that legitimately backgrounds a helper burns the whole timeout and is killed.

Refs: green `ansible.clj:163`, `process.clj:32,104,229`, `providers.clj:51`,
`workflow.clj:407`; red `ansible.ts:186`, `process.ts:26`, `runtime.ts:69`;
blue `ansible.py:160`, `process.py:25`, `runtime.py:100`, `providers.py:17`.
Each item executed in all three.

**15. CI does not explicitly install the inventory parser**

Green, Red, and Blue. Medium severity.

All three workflows install OpenTofu but do not explicitly install Ansible.
The round-trip test feeds a rendered inventory through `ansible-inventory`
and skips when that executable is absent. The audit observed local skips;
it did not cite CI logs proving a CI skip. Install Ansible explicitly and
require the parser test in CI so coverage does not depend on runner contents.

Coverage of several helpers is limited, but it is not absent. Green's
`interruption-stops-every-execution-helper` exercises `run-inherit` through
thread cancellation. Red and Blue's package-conventions tests exercise command
plan error continuation. Green's shared-package-conventions test invokes a
lifecycle validator. Missing cases include inherited-terminal spawn failure
and signal status propagation in Red and Blue, terminal SIGINT in the captured
runner, command-plan cleanup and successful output, and validator error
aggregation. `conventional-backend-advice` has only a callable check in the
Red and Blue package-conventions tests.

- `green/.github/workflows/ci.yml`, `red/.github/workflows/ci.yml`, `blue/.github/workflows/ci.yml`
- Verified: the skip fired in all three local runs.

**16. Command-line edges**

Green, Red, and Blue. Low severity.

Green drops `-f` when an option precedes the event
(`--dry-run create -f x.yml` runs the default file) and answers a bare `-f`
with an internal error instead of usage. Red accepts a YAML document that is
a list or scalar and exits 0. Blue rejects the `--` separator. The audit also
checked happy paths and start/end bounds. Unknown flags, missing files, and
bad YAML return exit 2 across the three colours.

- `green/src/green/cli.clj:166`, `red/src/cli.ts:102`
- Reproduced, 24 cases through all three.

**17. Documentation drift**

Green, Red, and Blue. Low severity.

- Green's `docco.html` was last regenerated on 2026-08-08, before lifecycle and providers existed; regenerating changes about 1,500 lines. The spec's namespace list (`index.html` §13) has 8 of 12 and the API index omits everything added since July.
- Green's spec and README say the default file is `green.edn` and desired state "is an EDN map"; the code defaults to `green.yml`. `build.clj`, README and the example `deps.edn` files still say `io.github.amiorin`.
- `green/src/green/tofu.clj:37` still promises exit -1 on a start failure; the code now returns 127.
- Red's `SPEC.md` types opts as `unknown` where the code says `any`, calls the embed option `in` where the code says `inFn`, and states every subprocess goes through the runtime seam.
- Blue's README naming table lists `green.edn`; the example launchers still suggest `blue==x.y.z`, which its CLAUDE.md forbids until a PyPI release exists.
- Nobody documents that Selmer HTML-escapes rendered file bodies and target paths, or that `after-while` receives input opts and replaces the result.

## Where the fixes would land

Almost no downstream package runs this week's SDK commits yet, which is also
why the freeze tightening in red and blue has not bitten anyone.

| Colour | Pinned SHA | Manifests | Who |
|---|---|---:|---|
| green | `a918861` (head) | 2 | once |
| | `3f33f5d` | 29 | every other package, colors-compute |
| | `ceb4159` | 4 | clickhouse, dotfiles, neon, wavehouse |
| red | `e24217c` (head) | 1 | once |
| | `7636bee` | 4 | neon-multi-node |
| | `db9bfe6` | 25 | every other package |
| blue | `ec33f05` / `e29a7fc` | 6 | once, colors-compute, neon-multi-node |
| | `290f313` | 54 | every other package and deployment payload |

## What was verified as identical

- Scheduler: linear, fork and join, branch structure and order, collapse on failure with worst exit, siblings that never reach the join, start and end bounds, next-function returning zero, one or many, throws with custom exits, nested forks including this week's cases, embeds with inherited and same-id-replaced advice, depth ordering with interleaved add-all.
- Advice truthiness: before-while and before-until use Clojure truthiness in all three; after-while and after-until key on the exit code.
- Generated bytes for ASCII lowercase-key input: backend JSON for local, s3, r2, gcs and conventional; constructs and deep-merge; inventory quoting and Python literals; recap parsing; tofu and ansible argv and env; scaffold create, delete and prune.
- Process exit codes 0, 3, 124, 127, 137, 143 and the timeout message; POSIX quoting of apostrophes, empty strings, variables, newlines and unicode.
- Lifecycle defaults and validator aggregation, provider required and secret messages, placeholder detection.
- The YAML scalar corpus from `once/test/parity/scalars.yml` produces matching descriptions under the fixture's normalization. The describers normalize whole-valued floats to integers. This checks the selected corpus, not identical runtime types or complete YAML compatibility.

## Fix first

1. Completed on 2026-09-12. Return 127 and 128+signal from the inherited-terminal runner in Red and Blue, route it through the runtime seam, and test failures and successor suppression.
2. Align the two renderers with Selmer on the empty string, `&#39;`, and unknown filters raising, then add apostrophe, empty-string and non-ASCII cases to the once parity fixture so `parity.sh` can see them.
3. Replace `localeCompare` with code-point ordering in red's tofu helpers, pass `ensure_ascii=False` in blue's five JSON calls, and decide `hcl-map` ordering once for all three.
4. Define launcher interrupt handling separately from timeout handling. Forward the first SIGINT once to each detached group, allow a bounded grace period, then kill survivors. Keep readers open during cleanup, preserve exit 130, and stop successors even when a child exits 0 during cleanup. Commands sharing the foreground group must not receive a duplicate SIGINT. Verify this with real launcher subprocesses before claiming graceful OpenTofu state recovery.
5. Define an explicit dynamic fork-to-join contract before changing singleton scheduling. A fork frame alone is insufficient because `same-origin?` and `step-units` still classify a single entry as an ordinary step. Specify the intended join and the zero-item result, preserve ordinary linear routing, and test N=0, N=1, N=3, failures, and nested forks. Address dry-run and event propagation through embeds separately.
6. Install Ansible in the three CI workflows, then regenerate `docco.html` and bring the green spec's namespace list, default file name and coordinates up to date.

## Follow-up contracts

Captured-command interruption needs launcher-level handling. Blue's
`asyncio.run` cancels the main task on SIGINT, and its cleanup must allow the
child's interrupt handler to finish before escalation. Green's thread
interruption tests do not prove OS signal handling. Red needs interrupt state
that prevents successors after its child finishes. A shared registry should
track active commands across concurrent branches. Windows console behavior
needs separate tests.

Test a real workflow launcher with a child that records SIGINT, writes a
cleanup marker after a brief delay, and exits. Require the cleanup marker,
launcher exit 130, and no successor execution. Also cover an interrupt-ignoring
child, concurrent branches, surviving descendants, timed and untimed commands,
and descendants that retain output pipes.

For singleton fan-out, a proposed workflow option maps a fork step to its
intended join. Retain the fork's opts and join target for zero, one, or several
items. Run intermediate steps normally. The declared join receives the saved
opts and branch results, including an empty collection for a successful empty
fan-out. Failed forks and explicit end bounds still stop execution. Keep
existing implicit joins for compatibility and update the affected examples
to declare their joins. This design remains follow-up work, not a scheduler
change in the inherited-terminal fix.

## Original audit method

- Ran each suite once: `bb test` and `clojure -X:test` in green, `bun install --frozen-lockfile && bun test && bun run typecheck` in red, `uv sync && uv run pytest` in blue.
- Smoke-ran all five examples in all three colours in scratch copies, then byte-diffed the generated `work/` trees and the dry-run output.
- Four parallel read-only audits: one per colour (every module read in full, suspicions reproduced by script) and one cross-colour pass that executed the same workflows, templates, YAML scalars, overlay values, JSON emitters, process calls and CLI arguments through all three and diffed the results.
- Spot-verified every high finding against the cited source lines before reporting.
