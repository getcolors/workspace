# Compute Provider Standard for Package Skills

Status: normative. The operations of §2, §4 and §5 have one implementation:
ONCE's `compute` namespace (`io.github.getcolors.once.compute`,
`package-once-red`'s `compute` export, `package_once_blue.compute`), which a
package calls with a spec value carrying its own registry. Reference
consumer: `clickstack` (green, red, blue); `posthog` is born conforming on
its second provider.
Consumers: every Package Skill that fills the `provider-compute` slot.
Sibling of `ssh-keypair.md`, `ssh-config.md`, and `compute-name.md`, which
govern the keys a provider template interpolates; this document governs how a
package advertises, selects, and proves a provider.

This document defines the single-node contract a Package Skill follows to
support more than one compute provider: what a provider entry declares, how a
template is chosen, what the compute stage hands to every later stage, what
the network looks like on every provider, and what evidence advertises a
provider at all.

It exists because the workspace already had three answers and one of them was
wrong in public. `once` renders nine providers from one registry and one
template directory per provider. `rybbit` copied the shape for two providers
and then shipped Package Skill payloads that document only one of them, so an
agent installing `package-rybbit-green` learns of DigitalOcean and never of
Vultr, while `repositories.json` says "on DigitalOcean" about a package whose
second deployment runs on Vultr. `walter`, `airflow`, and `vaultwarden` reach
ONCE's registry through a pin and advertise providers none of their fixtures
render. Two dozen other packages hardcode `:provider-compute must be
<one name>`, which is honest but leaves every port to be designed from scratch.
The port is the same design every time. This writes it down.

## 1. Scope

This revision defines the **single-node** contract: one machine with a public
IPv4 address, a provider firewall in front of it, and no private network. A
package whose machines bind a service to a VPC address, build per-peer
east-west rules, or number more than one node is out of scope until a
multi-node contract exists. Today that is `langfuse`, `automq`,
`mysql-agy`, `mysql-ha`, `postgres-agy`, `postgres-ha`, `k8s`, `clickhouse`,
and `k3s`. The managed-Kubernetes packages provision a control plane rather
than a machine and are never in scope. `dotfiles` provisions nothing.

A package with one provider conforms with a one-entry registry. Nothing here
obliges a second provider; everything here makes a second provider a copy of a
known shape rather than a design.

## 2. The registry

A package MUST own a registry that maps each provider it supports to what
selecting it implies:

```clojure
(def compute-providers
  {"vultr" {:required [:vultr-region :vultr-plan :vultr-os-id
                       :vultr-ssh-sources :vultr-http-sources]
            :secrets [:vultr-api-key]
            :tofu-env {:vultr-api-key "VULTR_API_KEY"}}
   "digitalocean" {:required [:digitalocean-region :digitalocean-size
                              :digitalocean-image :digitalocean-ssh-sources
                              :digitalocean-http-sources]
                   :secrets [:do-token]
                   :tofu-env {:do-token "DIGITALOCEAN_TOKEN"}}})
```

`:required` are the non-secret keys that provider's template interpolates.
`:secrets` are the credentials it needs through `COLORS_PAR_*`. `:tofu-env` is
the subset OpenTofu reads from the process environment itself. The same map,
in each colour's idiom, lives in `validate.ts` and `validate.py`; the three
MUST agree, and `scripts/parity.sh` is where they are proven to.

The keys of the registry are the **advertised** providers. A selection outside
it is refused with

```text
:provider-compute must be one of digitalocean, vultr
```

listing the advertised names sorted. Required keys, secrets, and the OpenTofu
environment MUST be derived from the selected entry, never from a second list
kept beside it: a provider added to one and not the other is how a package
comes to demand a token it never uses.

Provider keys are provider-scoped: `vultr-plan`, `digitalocean-size`,
`<provider>-ssh-sources`, `<provider>-http-sources`. Keys belonging to a
provider that is not selected MUST be accepted and ignored, never refused, so
one `colors.yml` can carry both blocks and switch providers by editing one
line. Validation that is specific to one provider — Vultr's numeric `os-id`,
DigitalOcean's refusal of a configured VPC — runs only when that provider is
selected.

The registry is the package's; the operations over it are not. A package
MUST hand its registry, its default provider and its source keys to ONCE's
`compute` namespace as one spec value —
`{:registry … :default … :sources {:non-empty [...] :may-be-empty [...]}}` —
and call ONCE for the refusal above, for the required keys, secrets and
OpenTofu environment of the selected entry, for the per-provider checks,
and for everything §4 and §5 name. A package that copies those functions
instead of calling them is how six packages came to hold four IPv6 parsers.
ONCE proves the three colours agree through its `compute` parity drivers;
the package's own tests cover its wiring, not the matrix.

The backend slot is not this document's. Packages keep reading ONCE's
`:provider-backend` registry for it.

## 3. Template selection

A provider is selected by directory, never by conditionals inside one file:

```text
tools/infrastructure/<provider>/main.tf
```

The rendered target stays `<stage>/main.tf`, so the stage directory, the state
key, and every consumer of the rendered tree are unaware which provider
produced it. A template MUST NOT branch on the provider name. The only
conditionals it MAY carry are the `<% if ssh-keygen %>` branch that
`ssh-keypair.md` §4 defines and optionals local to that provider, such as a
pinned image id. `rybbit` records why: a build is the only thing that proves a
provider's tree renders at all, and a conditional tree renders one branch per
build while claiming both.

Provenance is free. A package MAY render ONCE's template for a provider by
pin when it needs no resource ONCE's template lacks; `walter` and `airflow`
do. A firewall is such a resource, so a package that puts one in front of its
host owns that provider's template. A package MAY generate `.tf.json` beside
the template, as `rybbit` does for Vultr's per-CIDR rules; `clickstack`
achieves the same with `for_each` in the template and the standard prefers
neither.

**Adoption MUST NOT move an existing provider's state.** The resource
addresses and resource attributes of a provider the package already supported
MUST render byte-identically before and after the change; the committed
golden is the proof, and its diff MUST consist of the `params.provider` line
that §4 adds and nothing else. A package that renames `vultr_instance.node1`
while adopting this standard has planned a replacement of every live machine.

## 4. The `params` contract

Every provider's compute stage outputs one map, and every later stage reads
only that map:

```hcl
output "params" {
  value = {
    provider = "vultr"
    ip       = vultr_instance.clickstack.main_ip
    user     = "root"
    sudoer   = "root"
    name     = "<{ compute-name }>"
    ssh_key_id = vultr_ssh_key.machine.id   # keygen mode only
  }
}
```

- `provider` is the literal registry name the template belongs to, and it is
  new. It is what makes provider switching decidable (below).
- `ip` is the public IPv4 address: `ipv4_address` on DigitalOcean, `main_ip`
  on Vultr. Naming the wrong attribute fails as a missing output rather than
  as an unreachable host, which is the failure to prefer.
- `user` and `sudoer` are the login and the account that can become root.
  `uid` MAY be added by a provider whose image logs in as a non-root user, as
  ONCE's OCI template does.
- `name` is the resolved compute name of `compute-name.md` §2.
- `ssh_key_id` is the provider-side key resource of `ssh-keypair.md` §5,
  present in keygen mode and absent otherwise. The key MUST keep its
  underscore: ONCE's create matrix reads it as written, and a renamed key
  reads as a key the deployment does not own.

`build` and `--dry-run` render against per-provider fallback params on the
documentation address `192.0.2.10`, with the provider's real `user` and
`sudoer`, so a rendered tree can never point at a real machine. A real
converge MUST refuse when the compute output carries no `ip`, with the
message `compute produced no ip output; refusing to converge against the
documentation address`. `posthog` learned this from a live teardown that
converged against `192.0.2.10`; `clickstack` merged the fallback under the
output until this document.

**Provider switching is a rebuild, never an apply.** Every provider of a
package shares one state key, `<profile>/<package>-infrastructure.tfstate`.
A `provider-compute` edit on a profile that already holds a machine would
plan the old provider's destruction and the new provider's creation as one
apply, and `prevent_destroy` is the last line against that, not the first.
On every real `create` and every real `delete` the package MUST read the
existing `params` before it validates provider credentials — the read needs
backend credentials only — and:

- when `params.provider` is present and differs from the selected provider,
  MUST refuse with `state holds a <recorded> machine; set provider-compute
  back to <recorded> and delete first`. A delete is refused too, because a
  delete renders and destroys the *selected* provider's template and would
  otherwise validate the wrong credentials and touch the wrong lifecycle;
- when `params` is present without `provider` — a deployment created before
  the package adopted this standard — MUST refuse unless the selected
  provider is the package's default, which is the provider every such
  deployment runs.

The check runs before provider-secret validation so that a mistaken edit
reports the actionable error and not a missing token for the provider that
was never meant. In ONCE these are `read-state` (one read, `opts` first, the
reader passed in, a step error from the reader reported as `{:error …}` and
anything else propagated), `provider-state-errors`, `provider-validator`
(which takes the package's secret-errors thunk so ONCE never learns about
application secrets), `adopt-state` (fail-closed, no address override; a
package that wants one wraps it) and `resolved-compute`. The message
strings are ONCE's contract and MUST NOT be reworded by a consumer.

**An unreadable backend is not an empty state.** On a real `create` an
unreadable backend counts as no state, because a fresh clone has none. On a
real `delete` it MUST fail, with `could not read the infrastructure state for
the delete cleanup: <reason>`, rather than proceed with nothing to address; a
readable state without `params` leaves the address unset and the cleanup
skips itself.

## 5. The network contract

The provider firewall is the load-bearing layer. It admits inbound TCP 22
from `<provider>-ssh-sources`, inbound TCP 80 and 443 from
`<provider>-http-sources`, and nothing else; outbound is open. A package MUST
NOT manage ufw for those ports in its plays, and MUST NOT rely on the guest
firewall for its isolation claim: Docker's published ports bypass ufw through
the `DOCKER` chain, which is why the provider firewall is the one that counts.

The validator MUST refuse, before any provider call:

- an empty `<provider>-ssh-sources`, which renders a machine no one can reach
  and fails only at the first converge;
- any entry of either source key that is not a syntactically valid IPv4 or
  IPv6 CIDR, which OpenTofu would reject only once the apply reached the
  provider.

An empty `<provider>-http-sources` is allowed and means no public HTTP.
Which keys must be non-empty and which may be empty is the spec's `:sources`
map, by name, never by position; ONCE's `source-errors` and `cidr?` do the
checking.
`airflow` defaults an empty list to the whole internet; this standard refuses
instead, because a silent default-open in front of a database is worse than
a validation error. Both DigitalOcean and Vultr accept both address families;
a Vultr rule carries the family explicitly (`ip_type`), a DigitalOcean rule
infers it.

No VPC is created. DigitalOcean discovers the region's default VPC
(`data "digitalocean_vpc" "default"`, named `default-<region>`) and the
validator refuses `digitalocean-vpc-uuid` and `digitalocean-vpc-cidr`, as
`umami`, `posthog`, `rybbit`, and `alice` already do; a Vultr single-node
instance attaches no VPC. A package that needs a private network is a
multi-node package and outside §1.

### 5.1 Provider facts

What a live create verified, per provider. A package MAY extend this table in
its own documentation and MUST NOT state a fact here that no gate proved; in
particular, nothing below claims how either provider's firewall treats
private-interface traffic, because no single-node gate exercises it.

| | DigitalOcean | Vultr |
|---|---|---|
| Image key | `digitalocean-image: ubuntu-24-04-x64` | `vultr-os-id: 2284` (Ubuntu 24.04 LTS x64) |
| Login | `root` | `root` |
| Public address attribute | `ipv4_address` | `main_ip` |
| Machine key | `ssh_keys`, key ids; keygen via `digitalocean_ssh_key` | `ssh_key_ids`, ForceNew; keygen via `vultr_ssh_key` |
| Console name | `name`, updates in place | `label`, updates in place; never `hostname`, which is ForceNew and an OS reinstall |
| Firewall | `digitalocean_firewall`, inbound and outbound rules inline, CIDR lists | `vultr_firewall_group` plus one `vultr_firewall_rule` per CIDR, address and prefix as separate fields |
| Guest firewall on the image | not shipped enabled | ufw enabled with 22/tcp alone |
| Account key preflight | `ssh-keypair.md` §5, DigitalOcean REST | `ssh-keypair.md` §5, Vultr REST |

## 6. Keys the sibling standards own

- `<provider>-ssh-keys` follows `ssh-keypair.md`: absent means keygen mode,
  present means opt-out. Keygen mode MUST work on every advertised provider,
  which is why a provider template carries the keygen branch and why the
  registry never lists the key as required.
- `<provider>-name` follows `compute-name.md`: optional, the profile by
  default, resolved once. The registry never lists it as required.
- The `~/.ssh/config` block follows `ssh-config.md`, and is the same block
  whichever provider produced the address.

## 7. Fixtures, goldens, parity

A provider is advertised by evidence. For every provider in the registry a
package MUST commit one fixture per keypair mode — keygen and opt-out — and
one golden tree per fixture:

```text
test/fixtures/colors.yml                    # default provider, keygen
test/fixtures/optout.yml                    # default provider, opt-out
test/fixtures/colors-digitalocean.yml       # second provider, keygen
test/fixtures/optout-digitalocean.yml       # second provider, opt-out
```

`scripts/golden.sh` MUST render every fixture, and `scripts/parity.sh` MUST
render every fixture through every colour, diff the rendered trees, and diff
the three resource trees byte for byte. A provider that appears in the
registry without a golden is the failure `rybbit` documents: a unit test
over the registry passes while its template is missing.

The assertions the sibling standards place on goldens — no `$HOME/.ssh` path
and no dotted quad in the rendered local play — hold on every fixture, not
only the first.

## 8. Documentation

An agent learns a package from its Package Skill payload, not from its
README, and `rybbit` shows what happens when the two disagree. For every
advertised provider a package MUST name, in every colour's `SKILL.md` and its
`references/configuration.md`, the credential variable and the provider
keys; MUST name the providers in the README's architecture section and in
the root `index.html`; and MUST name them in the catalog recipe's summary and
keywords and in the `repositories.json` description. A provider documented
in one colour and not another is a parity failure that no script catches.

## 9. Adoption

- New packages are born conforming and born delegating to ONCE's `compute`
  namespace. `create-package-skill` references this document.
- Existing packages adopt behind their normal pin flow. Adoption on a
  package with one provider is a one-entry registry, a directory move that
  preserves every rendered byte but the `params.provider` line, the two
  refusals of §4, and the CIDR validation of §5; it obliges no second
  provider.
- `redis` was listed here as multi-node for a VPC binding nothing used; it
  dropped the binding and adopted the standard on both providers instead.
  Its Vultr golden changed by more than the `params.provider` line — the
  VPC resource and attachment left with it — which §3 permits only because
  no live deployment existed to move.
- `netbird` adopted the standard by delegation with every sibling standard
  already in place; both goldens changed by the provider line alone. Its
  firewall admits UDP 3478 from a third source list, `vultr-stun-sources`,
  beside §5's 22, 80 and 443: an extension a package MAY make when the
  service needs it, named in its documentation and carried by the spec as
  another `:may-be-empty` suffix, never a reason to manage a guest firewall.
- `rybbit` adopted the standard, delegating to ONCE, and is the one
  package whose spec default is not its documented first provider: its only
  legacy state is the live Vultr deployment, so `:default` is `vultr`, which
  is what the default is for. Its adoption kept every Vultr resource address
  and the generated per-CIDR rules, and changed the DigitalOcean golden by
  the empty-HTTP guard as well as the provider line, with no live droplet to
  move. It adopted the `~/.ssh/config` stage of `ssh-config.md` the same
  day, additively: four new local-play trees, no existing golden byte.
  `walter`, `airflow`, and `vaultwarden` advertise ONCE's
  providers and MUST either commit a fixture and golden per advertised
  provider or narrow the advertised set to the providers they render.
- Deployments created before adoption carry no `params.provider`. They keep
  working unchanged on the package's default provider, and the §4 legacy
  rule refuses them any other provider until they are deleted and
  re-created, which is the same rebuild a switch would need anyway.
- The multi-node packages of §1 wait for the multi-node contract. Nothing
  here applies to them, and nothing here should be copied into them by
  analogy: their firewall is a different design.

## 10. Conformance checklist

A package conforms when:

1. It owns a `compute-providers` registry whose keys are the advertised
   providers, agreeing across the three colours.
2. Required keys, secrets, and the OpenTofu environment derive from the
   selected registry entry alone.
3. An unadvertised provider is refused with the sorted list; keys of an
   unselected provider are ignored.
4. Templates live under `tools/infrastructure/<provider>/` and never branch
   on the provider name.
5. Every provider outputs `params` with `provider`, `ip`, `user`, `sudoer`,
   `name`, and `ssh_key_id` in keygen mode.
6. `build` and `--dry-run` render fallback params on `192.0.2.10`; a real
   converge refuses a missing `ip`.
7. A real create and a real delete refuse a provider that differs from the
   one recorded in state, and refuse a legacy state on any provider but the
   default, before validating provider credentials.
8. An unreadable backend is no state on create and a failure on delete.
9. The provider firewall admits 22, 80, and 443 from the two source keys and
   nothing else; the plays do not manage ufw for them.
10. Empty SSH sources and malformed CIDRs are refused before any provider
    call.
11. No VPC is created; DigitalOcean's configured-VPC keys are refused.
12. Keygen mode works on every advertised provider, and `<provider>-name` is
    optional.
13. One fixture per provider per keypair mode, each with a golden;
    `golden.sh` and `parity.sh` render all of them.
14. Every colour's SKILL payload, the README, the landing page, the catalog
    recipe, and `repositories.json` name every advertised provider.
15. Adoption leaves an existing provider's golden unchanged but for the
    `params.provider` line.
16. Goldens and parity fixtures are updated in the same change.
17. It delegates the operations of §2, §4 and §5 to ONCE's `compute`
    namespace rather than copying them; its own tests keep one wiring test
    per safety boundary and one spec-content test per colour, and drop the
    pure-function matrices ONCE tests.
