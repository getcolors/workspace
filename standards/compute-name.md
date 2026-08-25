# Compute Name Standard for Package Skills

Status: normative. Reference implementation: `alice` (green).
Consumers: every Package Skill that provisions a named compute resource.

This document defines what a Package Skill calls the machines it creates.

It exists because the workspace already agreed on the answer and then wrote it
down twenty times by hand. Every package requires a provider-scoped name key —
`digitalocean-name`, `vultr-name` — and every deployment sets that key to its
own profile. A required key whose only correct value is another key's value is
not configuration; it is a transcription step, and transcription drifts. It
drifted in `alice-digitalocean`, which named its Droplet `alice` while its
profile, its machine keypair, its `~/.ssh/config` alias, and its OpenTofu state
key all said `alice-digitalocean`.

## 1. The rule

A package MUST name compute resources after the profile by default. The profile
is the deployment's identity: it keys remote state as `<profile>/<stage>.tfstate`,
it names the machine keypair and its provider-side registration, it is the
`~/.ssh/config` alias an operator types, and it is what a reader recognizes in a
provider console. The machine's own label MUST NOT be the one place that
disagrees.

A package MUST NOT require a name key in desired state. A fresh `colors.yml`
that omits it is complete, and the rendered template names the resource
`<profile>`.

## 2. The override

A package MAY accept an optional provider-scoped name key — `digitalocean-name`,
`vultr-name`, and so on — for an account that needs a different label: a naming
policy a profile cannot satisfy, or an existing resource being adopted.

Presence is the only switch, matching how `digitalocean-vpc-uuid` selects
between a pinned VPC and regional discovery, and how `digitalocean-ssh-keys`
selects between opt-out and keygen. Absent, blank, or `REPLACE_ME` means the
profile. Anything else is the name, and a package MUST validate it against the
provider's naming rules rather than passing it through unread.

A package MUST resolve the effective name once, in one function, and render
that. Templates MUST NOT branch on whether the override is present.

## 3. Derived names

Resources named around the machine — a firewall, a VPC, a per-node suffix —
MUST derive from the same resolved name, not from the raw override key and not
from a second copy of the profile. One function answers "what is this
deployment's machine called", and everything that needs a label asks it.

## 4. What a rename does not do

Changing the name renames the resource at the provider. It does not rename the
running machine: cloud-init sets the guest hostname from the name at creation,
and a later rename never revisits it. `alice-digitalocean` demonstrated this —
its Droplet answered `hostname` with `alice` after the profile had long since
become its identity everywhere else.

A package MUST therefore treat a name change as taking effect on the next
create, not as a repair to a running host. Packages whose machines are
ephemeral get the correct hostname for free on the next cycle; packages with
long-lived hosts SHOULD say plainly that the guest hostname lags until a
rebuild.

## 5. Removing `package`

A package MUST NOT require a `package` key in desired state. Every package
supplied it as a default and then validated that it equalled the package's own
constant name, which is a key that can hold exactly one value and therefore
carries no information. Remove it from desired state, from required keys, and
from validation together.

## 6. Adoption

`alice` implements this standard. Every other package still requires a name key
and MUST migrate. Migration is a no-op on the wire for a deployment whose name
key already equals its profile, which is all of them but a handful — those
render an identical template before and after, and the change is visible only
as a shorter `colors.yml`. The exceptions named a machine after the package
rather than the deployment and will show a rename in their next plan; §4
governs what that rename does and does not achieve.
