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
decide whether the block names an identity file, two different host-key
policies, and two marker shapes — one of which cannot distinguish two packages
that chose the same profile. Ten further packages, `clickstack` included until
this document landed, write no block at all.

## 1. Scope: who writes a block

A package MUST manage a `~/.ssh/config` block when it provisions a host the
operator is expected to reach over SSH. That is the trigger, and it is
deliberately **not** "the package generated a key": `k3s`, `k8s`, and `alice`
write useful blocks while in opt-out mode, because an alias is worth having
whoever owns the key.

Out of scope: `dotfiles` and any package with no machine. Packages whose hosts
are unreachable by design (no public SSH, no jump host) MUST NOT write a block
that cannot connect.

What keygen mode changes is one line of the block, not whether it exists (§3).

## 2. The alias and the marker

The alias is the **profile**, unchanged. `ssh-keypair.md` §2 already argues
that the profile is globally unique by construction, because it keys remote
state in a shared backend; the same argument makes it safe here. A package
MUST NOT introduce a separate configuration key for the alias.

The marker MUST carry both the package name and the alias:

```yaml
marker: "# {mark} <package> {{ host_alias }} ANSIBLE MANAGED BLOCK"
```

Both halves are load-bearing. The alias separates two deployments of one
package. The package name separates two packages that were pointed at the same
profile, which nothing prevents — `once` and `walter` both derive the alias
from `profile`, and a marker carrying only the alias would let either silently
rewrite the other's block. `once` currently omits the package name and is the
outlier; see §7.

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

- `IdentityFile` and `IdentitiesOnly` appear **only in keygen mode**, where the
  package knows the key because it generated it. In opt-out mode the operator
  supplied the key and has their own arrangements for finding it; guessing is
  worse than silence. This is `walter`'s existing shape, generalized.
- `StrictHostKeyChecking accept-new` trusts the host key on first connection
  and refuses it if it ever changes afterwards. That is the right default for a
  machine this deployment just created: no interactive prompt during
  convergence, and a real warning if the address is ever recycled to a stranger.
  A package MAY instead pin the key in `~/.ssh/<profile>.known_hosts`, which
  `ssh-keypair.md` §2 already reserves and which no package writes today; if it
  does, it MUST also emit `UserKnownHostsFile` and MUST NOT weaken
  `StrictHostKeyChecking`.
- `ForwardAgent no` is explicit rather than implied. It is already the OpenSSH
  default, and stating it means a later `Host *` block cannot turn it on for a
  machine that has no use for it.

Multi-node packages write one block per node, aliased `<profile>-<node>`.

## 4. Lifecycle

The block is written by a dedicated `ansible-local` stage that runs against
`localhost` with `connection: local`, and by nothing else. One task, one file.

**Create.** The stage runs after the compute stage, which is the first point at
which the address exists, and before the stage that converges the machine.

**Delete.** The stage runs again with `block_state: absent`, **before** the
compute destroy.

That ordering is the exact opposite of the keypair's, and both are right. A
config block that outlives its host is stale but harmless, so removing it early
costs nothing. A key that predeceases its host locks the operator out of a
machine that still exists, which is why `ssh-keypair.md` §3.3 puts the key
last. A package MUST NOT "tidy" these into agreement.

Verbs other than `create` and `delete` MUST NOT write the block. A `stop` or
`start` that leaves the address unchanged has nothing to say about it.

## 5. Ownership and the wildcard preflight

Two local checks run on a real `create`, before the stage renders.

**Never adopt.** A `Host <profile>` stanza that exists in `~/.ssh/config`
outside our markers MUST be an error, never overwritten. The operator wrote it
by hand or another tool owns it, and the block may be their only record of how
to reach something. The message MUST name the file and line and leave the
decision with the human, mirroring `ssh-keypair.md` §3.2.

**The wildcard trap.** `ssh_config` takes the **first** value it obtains for
most keywords, and `blockinfile` appends by default. A `Host *` or `Match`
stanza earlier in the file that sets `User`, `IdentityFile`, or
`IdentitiesOnly` therefore wins over the managed block, and the resulting
connection authenticates as the wrong user with the wrong key while the block
reads as if it should have worked.

Packages MUST insert the block at the **top of the file**:

```yaml
insertbefore: BOF
```

`BOF` rather than a regex, and this is not a stylistic choice. `blockinfile`
anchors `insertbefore` on the **last** match, which is the wrong end of the
file, and it has no `firstmatch` parameter — that belongs to `lineinfile`. A
regex intended to find the first `Host` line therefore finds the last one and
places the block below every wildcard it was meant to outrank.

A `BOF` insert has one failure of its own. Options standing **above** the first
`Host` or `Match` line are global, and a block inserted above them would
capture them into its own stanza, narrowing a global setting to one host
without saying so. Packages MUST detect that layout on a real `create` and
refuse, naming the line and offering the recovery: move those options below the
managed block, or into an explicit `Host *` stanza at the end.

Refusing is the right answer rather than falling back to appending. A file
written that way is one where correct placement and correct meaning genuinely
conflict, and the operator is the one who can resolve it.

## 6. Build determinism

`build` and `--dry-run` MUST NOT read, create, or modify `~/.ssh/config`, on
the same reasoning as `ssh-keypair.md` §6.

The rule that makes this hold in practice: **run-time facts reach the play as
Ansible extra-vars, never through Selmer.** The address, the user, the alias,
and `block_state` are supplied at execution time, so the rendered playbook is
byte-identical whether or not the machine exists, and a package that commits
goldens commits no IP address. Only desired state that a `build` genuinely
knows — whether the package is in keygen mode, and therefore whether the
`IdentityFile` pair is present at all — may be templated.

`walter`'s playbook already documents this distinction; this makes it binding.

## 7. Copy, do not share

Each package MUST own its own copy of the local play. This is deliberately the
opposite of `ssh-keypair.md`, where `clickstack` reuses `once`'s implementation
so that one standard has one implementation.

The asymmetry is about what a pin bump can do. `ssh.clj` acts on
profile-named files that only its own deployment uses, so sharing it makes an
upstream fix reach every consumer. The local play writes into a file the
operator shares with every other host they reach, so sharing it would let an
unrelated change upstream — an added `ProxyJump`, a different host-key policy —
rewrite that file at pin-bump time in a repository nobody was working in.
`walter` reached this conclusion independently and its source comment records
it.

Three files against that exposure is the right trade.

## 8. Adoption

- New packages are born conforming; `create-package-skill` references this
  document.
- The seven packages that already write a block adopt behind their normal pin
  flow. The changes are small in every case: `once` gains the package name in
  its marker, `walter` and `once` gain the host-key policy, `k8s` stops
  hardcoding `User root`, and all seven gain the `insertbefore` placement.
- **`once`'s marker change needs migration, not just a rename.** A block
  written under the old marker is invisible to the new one, so a converge would
  leave the old stanza in place and add a second `Host` block beside it, with
  the stale one winning under first-match. The adopting change MUST remove the
  old block before writing the new one, and MUST NOT be shipped as a bare
  marker edit.
- The ten packages that write no block adopt when they next need one. Nothing
  breaks in the meantime; the operator keeps typing the address.

## 9. Conformance checklist

A package conforms when:

1. It writes a block if and only if it provisions an SSH-reachable host.
2. The alias is the profile, with no separate configuration key.
3. The marker carries the package name and the alias.
4. `IdentityFile`/`IdentitiesOnly` appear in keygen mode and are absent in
   opt-out mode.
5. `StrictHostKeyChecking accept-new` and `ForwardAgent no` are present, or a
   pinned `known_hosts` replaces the former without weakening it.
6. Create writes the block after compute and before convergence; delete removes
   it before the compute destroy.
7. Address, user, alias, and `block_state` arrive as Ansible extra-vars, not
   through Selmer.
8. `build` and `--dry-run` never touch `~/.ssh/config`, and goldens contain no
   address.
9. An unmarked `Host <profile>` stanza is an error, never overwritten.
10. The block is inserted with `insertbefore: BOF`, and a file whose first
    option stands above the first `Host` line is an error rather than a
    silently narrowed global.
11. The play is the package's own copy, not a shared upstream one.
12. Goldens updated in the same change.
