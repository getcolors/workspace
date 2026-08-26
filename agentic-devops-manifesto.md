# The Agentic DevOps Manifesto

*by Colors*

You are right to distrust an agent holding cloud credentials.

The pitch you have been hearing goes like this. Give the model your provider
APIs, describe what you want in English, and it converges your infrastructure
while you watch. Anyone who has run production hears the problem straight away.
Somebody now has to read back every operation the thing performed and decide
whether each one meant what it looked like. That is not less work than doing it
yourself. It is the same work, done later, with worse information, on somebody
else's mistakes.

We agree. So we do not build that.

What follows is what we build instead, and what it costs. Every claim below is
implemented in the repositories of this workspace, and where we get it wrong we
have said so.

## 1. The agent writes the program. The program touches the cloud.

An agent calling provider APIs directly needs a human per operation, or it gets
no human at all. An agent writing a convergence program needs a human per change
to that program, and that one reading covers every run afterwards.

That ratio is the entire argument. It is not a claim about intelligence, safety
training, or how good the models got this year. It is arithmetic about where the
reviews go.

## 2. You review a diff, not a transcript.

A transcript of API calls is evidence of what happened. You have to reconstruct
intent from it, and you can only do that after the effects have landed.

A diff against known-good code is a proposal. It sits still. It has line
numbers. Your existing review habits work on it, and so does `git blame` six
months later when the thing breaks.

Both need a human. Only one of them lets the human say no.

## 3. Convergent, not deterministic.

We will not tell you the program does the same thing every time, because it does
not. Run the same OpenTofu configuration twice and you can get two outcomes. The
provider API changed. A resource is still eventually consistent. You hit a
quota. `apt-get install` pulled a newer package this month. An image tag moved.

What a Colors package gives you is idempotence, a declared desired state, a plan
you can read before anything happens, state that lets you spot drift, and
somewhere to put guardrails. That is more useful than determinism and it is a
different promise. Selling it as determinism sets you up to catch the tool
breaking a promise nobody should have made, and then you distrust it for the
wrong reason.

## 4. The plan is where permission is granted.

Every Colors launcher has three gears before it changes anything:

```sh
./green build              # render .colors/<profile>/, no provider calls, no credentials
./green create --dry-run   # walk the DAG, skip every side effect
./green create             # converge for real
```

`build` and `--dry-run` work on a fresh checkout with an empty environment. That
is deliberate. It means a reviewer can check what an agent proposes without
holding a single credential, which makes review something a second person can do
rather than a privilege of whoever has the keys.

Validation failure exits 2 and lists every problem at once, not the first one.
An agent iterating against a tool that reports one error per run learns to guess.

## 5. Guardrails live in the repository, not in the operator's attention.

Every deployment's `colors.yml` carries this:

```yaml
compute-prevent-destroy: true
```

Lifting it takes an explicit one-run environment override. Editing the committed
flag is out of bounds for humans and agents alike, and it is out of bounds
because it is written down in every `CLAUDE.md` in the workspace, not because we
trust everyone to remember.

The second guard matters more and is less obvious. `profile` keys the remote
state at `<profile>/<stage>.tfstate` and separates every project sharing one R2
bucket. Overlay it from the environment and you point one deployment at
another's state. So the packages refuse to run when `COLORS_PAR_PROFILE` is set,
and the refusal has a test of its own in `netbird/test/clj/io/github/getcolors/netbird/validate_test.clj:116`.

An agent hitting that guard has hit a wall, not a puzzle. That is the wall
working.

## 6. Hallucination is the least of your problems.

A hallucinated API call usually errors out. Loud, immediate, harmless.

The output that hurts is the plausible, well formed call that succeeds.
Deleting the resource that looked right. Opening `0.0.0.0/0`. Writing to the
wrong account or the wrong state file. Nothing about that trips a review for
hallucination, because nothing about it is a hallucination. It is a correct
operation aimed at the wrong thing.

Which is why "check the agent's output for mistakes" is not a safety strategy.
The guards in thesis 5 catch these. Reading the transcript does not.

## 7. Golden files are the only coverage infrastructure allows.

No unit test tells you a cloud account has the right firewall rules, so
demanding test coverage before you trust an agent is asking for something that
does not exist for anybody, agent or not.

What does exist is a byte comparison of what the program renders. The `netbird`
package holds 52 golden files across two fixtures, covering the OpenTofu
templates, the Ansible plays, the systemd units, the backup scripts and the
resource addresses. Change a step and the diff is in front of you before a
single provider call happens.

Two fixtures rather than one, because the SSH Keypair Standard has two modes and
conformance means both the keygen path and the opt-out path hold.

`once/scripts/parity.sh` does the same job across languages. One fixture, three
implementations, eight provider variants, `diff -qr` on the results. Green, red
and blue produce identical trees or the change is not finished.

Read a golden diff after a pin bump. Never run `bb golden:accept` to make a
failure go away.

## 8. Every edge is a pinned SHA.

Not a version range. Not `main`. A forty character commit:

```clojure
(def ^:private netbird-sha "7b0f784a17d453e0b2ec726d9a37e84db78e84d4")
```

A commit in `green/` is invisible in `netbird/` until it is pushed and the pin
moves. A change spanning two repositories is two commits in two repositories,
upstream pushed first. `bb pin` stamps the launcher after a push, so pins
describe history rather than intent.

Agents are good at producing text that looks like a SHA. Never let one invent a
pin, and never hand-edit one. To work across a boundary without pinning, point
the launcher at a working tree with `GREEN_LIB_ROOT`, `NETBIRD_LIB_ROOT` and
their siblings.

## 9. The copied launcher is where we get it wrong.

Installed launchers are copies, not symlinks. `npx skills update -p` rewrites
the payload under `.agents/skills/package-*/` and leaves the root `./green`
alone, so the project keeps running the old pin while `skills-lock.json` claims
the new one. The copy is a separate step:

```sh
npx skills update -p
cp .agents/skills/package-once-green/green green    # and red, blue
```

We publish this because a manifesto that only lists the parts that work is
marketing. A perfectly reviewed program you are not running gives you nothing,
and this is the way we most often end up not running it. `once-colors` diffs
root against payload in CI to catch it.

The launcher itself is written to be as small as we can make it. Its own header
says why: "A copied payload is the one place in this project where code cannot
be tested, so nothing that can live elsewhere should live here."

## 10. One file is editable. Everything else is generated or secret.

`colors.yml` is the only file a human or an agent edits in a deployment. It
holds kebab-case keys and non-secret values.

Credentials are `COLORS_PAR_<UPPER_SNAKE_KEY>` environment variables in a
gitignored `.envrc.private`, overlaid onto the matching key at run time. They
never appear in `colors.yml`, in generated output, in documentation, or in chat.
`.colors/` is generated. Never edit it, never read it as source, never commit
it.

The payoff is that the whole desired state of a production system fits in one
readable file that contains nothing dangerous. `netbird-vultr/colors.yml` runs
to a few dozen keys and its header names every credential the deployment needs
without holding one, along with the list of secrets nobody supplies at all: the
relay secret, the session cookie key, the store encryption key, Authentik's
database password, the OIDC client secret and the durable automation token are
all generated on the server and never leave it.

The exception is documented in the same header. The backup recovery key is
operator-supplied, because a key generated on the server would be lost with the
server it protects.

## 11. Authorization is a phase, not a checkbox.

Our `create-package-skill` workflow puts the agent in three phases and holds it
there.

Phase 1 is conversation only. No files created, modified or deleted. No plan
written to disk. The agent establishes what is being built and what it is
allowed to do, including whether it may create repositories, push commits, move
pins, spend money on cloud resources, or touch DNS. It stays there until the
operator says, in so many words, proceed.

Phase 2 creates exactly four files: `colors.yml`, `.gitignore`, `.envrc` and an
ignored `.envrc.private` for the operator to fill in. Then it stops again. The
agent does not read, display, copy or validate the contents of
`.envrc.private`.

Phase 3 is autonomous, and it is autonomous because two humans-in-the-loop
already happened at the points where the decisions were.

"Ask before doing anything dangerous" degrades into asking about everything,
which trains the operator to approve without reading. Phases put the questions
where the answers change the work.

## 12. The program knows nothing about the world it acts on.

Determinism in your program buys you no determinism about reality, and the gap
is where the real work is.

NetBird's ownership transfer needs one manual sign-in to Authentik. No
convergence step performs it. Run create, sign in, run create again.

HyperDX binds no OTLP receivers until convergence has created the first team, so
a ClickStack server that looks healthy accepts nothing until an ordering
constraint that appears in no documentation has been satisfied.

Neither of those fell out of reading code. Both came from running it against a
real provider and reading what came back. An agent that has never converged
anything will not find them, and a manifesto that implies otherwise is lying to
you.

## 13. Some work has no desired state, and forcing it there is a mistake.

Rotate this credential now. Drain this node. Find out why the disk filled.

An investigation has no steady state to converge on. Push it through a
convergence program and you write a lot of code that runs once. Direct
agent-to-API work is the right tool for that, with scoped credentials and an
audit log, not with a human reading back every operation afterwards.

We build desired-state packages because most infrastructure work is
desired-state shaped. Most is not all, and a position that cannot say where it
stops is not a position.

## What we are not claiming

We are not claiming the agent is reliable. We are claiming its output is
reviewable, and that the review covers every future run rather than one.

We are not claiming the program is deterministic. We are claiming it is
idempotent, that it shows you a plan first, and that it keeps state so you can
see drift.

We are not claiming you can stop paying attention. The guards exist because
attention runs out. So does ours. That is what they are for.

The stack is `green`, `red` and `blue` for the engine, Package Skills for the
things you install, and a `colors.yml` per deployment for the state you want.
It is all on GitHub under `getcolors`. Read a golden diff and decide for
yourself.
