# SSH Config Standard for Package Skills

Status: normative. Reference implementation: `clickstack` (green).
Consumers: every Package Skill that provisions a host the operator will reach
over SSH. Sibling of `ssh-keypair.md`, which governs the key itself.

This document defines how a Package Skill manages the `~/.ssh/config` entry
that lets an operator type `ssh <profile>` instead of reconstructing an
address, a user, and an identity file by hand.

It exists because seven packages already do this and no two do it the same
way. `once`, `walter`, `alice`, `k3s`, `k8s`, `postgres-agy`, and `postgres-ha`
each ship an `ansible-local` stage whose only job is one `blockinfile` task
against `~/.ssh/config`. Between them they use three different mechanisms to
decide whether the block names an identity file, two host-key policies, and two
marker forms, one of which repeats the package name the profile already
carries. Ten further packages, `clickstack` included until this document
landed, write no block at all.

## 1. Scope: who writes a block

A package MUST manage a `~/.ssh/config` block when it provisions a host the
operator is expected to reach over SSH. That is the trigger, and it is not
"the package generated a key". `k3s`, `k8s`, and `alice` write useful blocks
in opt-out mode, because an alias is worth having whoever owns the key.

Out of scope: `dotfiles`, and any package with no machine. A package whose
hosts are unreachable by design, with no public SSH and no jump host, MUST NOT
write a block that cannot connect.

Keygen mode changes one line of the block, not whether it exists (§3).

## 2. The alias and the marker

The alias is the profile, unchanged. `ssh-keypair.md` §2 already argues that
the profile is globally unique by construction, because it keys remote state in
a shared backend. The same argument holds here. A package MUST NOT introduce a
separate configuration key for the alias.

The marker MUST carry the alias and nothing else:

```yaml
marker: "# {mark} {{ host_alias }} ANSIBLE MANAGED BLOCK"
```

The profile already names the package. Every profile in this workspace is
`<package>-<suffix>`: `clickstack-vultr`, `walter-oci`, `k3s-hetzner`,
`once-colors`. A marker carrying the package name too would say it twice, as
`# BEGIN clickstack clickstack-vultr`.

The collision a package name would guard against cannot happen. Two packages
sharing one profile would already be fighting over `~/.ssh/<profile>`, because
`ssh-keypair.md` §2 puts all SSH state in one flat profile-named directory. A
deployment that gets that far is broken before it reaches this file, and a
longer marker would not save it.

`once` already writes this marker. The other six prepend their package name and
are the ones that must change; see §8.

## 3. The block

```sshconfig
Host <profile>
    HostName <ip>
    User <user>
    Port 22
    IdentityFile ~/.ssh/<profile>      # keygen mode only
    IdentitiesOnly yes                 # keygen mode only
    StrictHostKeyChecking accept-new
    ForwardAgent no
```

- `IdentityFile` and `IdentitiesOnly` appear only in keygen mode, where the
  package knows the key because it generated it. In opt-out mode the operator
  supplied the key and has their own arrangements for finding it. Guessing is
  worse than silence. This is `walter`'s existing block, generalized.
- `StrictHostKeyChecking accept-new` trusts the host key on first connection
  and refuses it if it ever changes afterwards. That suits a machine this
  deployment just created. Convergence gets no interactive prompt, and the
  operator gets a real warning if the address is ever recycled to a stranger.
  A package MAY instead pin the key in `~/.ssh/<profile>.known_hosts`, which
  `ssh-keypair.md` §2 reserves and no package writes today. A package that does
  MUST also emit `UserKnownHostsFile`, and MUST NOT weaken
  `StrictHostKeyChecking`.
- `ForwardAgent no` is explicit rather than implied. OpenSSH already defaults
  to it, and stating it stops a later `Host *` block turning it on for a
  machine that has no use for it.

Multi-node packages write one block per node, aliased `<profile>-<node>`.

## 4. Lifecycle

A dedicated `ansible-local` stage writes the block, running against `localhost`
with `connection: local`. Nothing else touches the file. One task, one file.

**Create.** The stage runs after the compute stage, which is where the address
first exists, and before the stage that converges the machine.

**Delete.** The stage runs again with `block_state: absent`, before the compute
destroy.

That ordering reverses the keypair's, and both are right. A config block that
outlives its host is stale but harmless, so removing it early costs nothing. A
key that predeceases its host locks the operator out of a machine that still
exists, which is why `ssh-keypair.md` §3.3 removes the key last. A package MUST
NOT tidy these into agreement.

Verbs other than `create` and `delete` MUST NOT write the block. A `stop` or
`start` leaves the address unchanged and has nothing to say about it.

## 5. Ownership and placement

Two local checks run on a real `create`, before the stage renders.

**Never adopt.** A `Host <profile>` stanza that sits in `~/.ssh/config` outside
our markers MUST be an error, never overwritten. The operator wrote it by hand,
or another tool owns it, and it may be their only record of how to reach
something. The message MUST name the file and the line, and leave the decision
with the human, mirroring `ssh-keypair.md` §3.2.

**The wildcard trap.** `ssh_config` takes the first value it obtains for most
keywords, and `blockinfile` appends by default. A `Host *` or `Match` stanza
earlier in the file that sets `User`, `IdentityFile`, or `IdentitiesOnly`
therefore beats the managed block. The connection then authenticates as the
wrong user with the wrong key, while the block reads as if it should have
worked.

Packages MUST insert the block at the top of the file:

```yaml
insertbefore: BOF
```

`BOF` rather than a regex, and not as a matter of taste. `blockinfile` anchors
`insertbefore` on the last match, which is the wrong end of the file, and it
has no `firstmatch` parameter. That belongs to `lineinfile`. A regex meant to
find the first `Host` line therefore finds the last one, and places the block
below every wildcard it was meant to outrank.

A `BOF` insert has one failure of its own. Options standing above the first
`Host` or `Match` line are global, and a block inserted above them would
capture them into its own stanza, narrowing a global setting to one host
without saying so. Packages MUST detect that layout on a real `create` and
refuse. The message MUST name the line and offer the recovery: move those
options below the managed block, or into an explicit `Host *` stanza at the end
of the file.

Refusing beats falling back to appending. In such a file, correct placement and
correct meaning conflict, and only the operator can resolve it.

## 6. Build determinism

`build` and `--dry-run` MUST NOT read, create, or modify `~/.ssh/config`, on
the same reasoning as `ssh-keypair.md` §6.

One rule makes this hold. Run-time facts reach the play as Ansible extra-vars,
never through Selmer. The address, the user, the alias, and `block_state`
arrive at execution time, so the rendered playbook is byte-identical whether or
not the machine exists, and a package that commits goldens commits no IP
address. Only desired state a `build` already knows may be templated, which
means keygen mode, and therefore whether the `IdentityFile` pair appears at
all.

`walter`'s playbook already documents this distinction. This makes it binding.

## 7. Copy, do not share

Each package MUST own its copy of the local play. This reverses
`ssh-keypair.md`, where `clickstack` reuses `once`'s implementation so that one
standard has one implementation.

The difference is what a pin bump can reach. `ssh.clj` acts on profile-named
files that only its own deployment uses, so sharing it carries an upstream fix
to every consumer. The local play writes into a file the operator shares with
every other host they reach. Sharing that play would let an unrelated upstream
change, an added `ProxyJump` or a different host-key policy, rewrite that file
at pin-bump time in a repository nobody was working in. `walter` reached this
conclusion independently, and its source comment records it.

Three duplicated files cost less than that.

## 8. Adoption

- New packages are born conforming. `create-package-skill` references this
  document.
- The seven packages that already write a block adopt behind their normal pin
  flow. `once`'s marker conforms; `walter`, `alice`, `k3s`, `k8s`,
  `postgres-agy`, and `postgres-ha` prepend their package name and must drop
  it. `walter` and `once` gain the host-key policy, `k8s` stops hardcoding
  `User root`, and all seven gain the `insertbefore: BOF` placement and the
  leading-option refusal beside it.
- **A marker change is a migration, not a rename.** The new marker cannot see a
  block written under the old one, so a converge leaves the old stanza in place
  and adds a second `Host` block above it. First-match means the new block
  wins, and the stale one sits there misleading whoever reads the file next.
  The adopting change MUST remove the old block before writing the new one,
  through a second `blockinfile` task carrying the old marker with
  `state: absent`. It MUST NOT ship as a bare marker edit. The removal task
  stays for one pin cycle, then goes.
- **The never-adopt check MUST recognise the superseded marker for that same
  window.** A block under the old marker still belongs to the package. A check
  that knows only the new marker reads a `Host <profile>` stanza it did not
  write, and refuses, blocking the migration meant to clean it up. The
  reference implementation hit this on the converge after its own marker
  changed. Retire the old marker from the check and from the removal task
  together, or not at all.
- The ten packages that write no block adopt when they next need one. Nothing
  breaks meanwhile; the operator keeps typing the address.

## 9. Conformance checklist

A package conforms when:

1. It writes a block if and only if it provisions an SSH-reachable host.
2. The alias is the profile, with no separate configuration key.
3. The marker carries the alias alone, because the profile already names the
   package.
4. `IdentityFile` and `IdentitiesOnly` appear in keygen mode and are absent in
   opt-out mode.
5. `StrictHostKeyChecking accept-new` and `ForwardAgent no` are present, or a
   pinned `known_hosts` replaces the former without weakening it.
6. Create writes the block after compute and before convergence. Delete removes
   it before the compute destroy.
7. Address, user, alias, and `block_state` arrive as Ansible extra-vars, not
   through Selmer.
8. `build` and `--dry-run` never touch `~/.ssh/config`, and goldens carry no
   address.
9. An unmarked `Host <profile>` stanza is an error, never overwritten.
10. The block is inserted with `insertbefore: BOF`, and a file whose first
    option stands above the first `Host` line is an error rather than a
    silently narrowed global.
11. The play is the package's own copy, not a shared upstream one.
12. Goldens updated in the same change.

## The copies are checked as one

`workspace/scripts/package-copies.py` clusters every package's copy of the
module and the play by content, with the package name normalised out, and
fails on any cluster it cannot name: the multi-node packages' per-node
aliases and the §8 migrations still owed are named variants, anything else
is drift. A change to the reference implementation is finished when that
script is green again, not when clickstack's tests pass.

## Note added 2026-09-04

The preflight MUST resolve `~/.ssh/config` the way the local play's `~` does:
from `$HOME` first, falling back to the runtime's notion of the home
directory. A green copy that reads only the JVM's `user.home` can approve
one file while Ansible edits another when the two differ. `rybbit` resolves
it from `$HOME`; the other green copies (`clickstack`, `signoz`,
`agent-network`, `posthog`, `redis`) still read `user.home` alone and owe
the same one-line change.

